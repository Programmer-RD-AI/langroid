import logging
import os
from typing import List, Optional, Tuple

from chromadb.api.types import EmbeddingFunction
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.conversions.common_types import ScoredPoint
from qdrant_client.http.models import (
    Batch,
    CollectionStatus,
    Distance,
    Filter,
    SearchParams,
    VectorParams,
)

from llmagent.embedding_models.base import (
    EmbeddingModel,
    EmbeddingModelsConfig,
)
from llmagent.mytypes import Document
from llmagent.utils.configuration import settings
from llmagent.vector_store.base import VectorStore, VectorStoreConfig

logger = logging.getLogger(__name__)


class QdrantDBConfig(VectorStoreConfig):
    type: str = "qdrant"
    cloud: bool = True
    url = "https://644cabc3-4141-4734-91f2-0cc3176514d4.us-east-1-0.aws.cloud.qdrant.io:6333"

    collection_name: str | None = None
    storage_path: str = ".qdrant/data"
    embedding: EmbeddingModelsConfig = EmbeddingModelsConfig(
        model_type="openai",
    )
    distance: str = Distance.COSINE


class QdrantDB(VectorStore):
    def __init__(self, config: QdrantDBConfig):
        super().__init__()
        self.config = config
        emb_model = EmbeddingModel.create(config.embedding)
        self.embedding_fn: EmbeddingFunction = emb_model.embedding_fn()
        self.embedding_dim = emb_model.embedding_dims
        self.host = config.host
        self.port = config.port
        load_dotenv()
        if config.cloud:
            self.client = QdrantClient(
                url=config.url,
                api_key=os.getenv("QDRANT_API_KEY"),
                timeout=config.timeout,
            )
        else:
            self.client = QdrantClient(
                path=config.storage_path,
            )

        # Note: Only create collection if a non-null collection name is provided.
        # This is useful to delay creation of vecdb until we have a suitable
        # collection name (e.g. we could get it from the url or folder path).
        if config.collection_name is not None:
            self.create_collection(config.collection_name)

    def clear_empty_collections(self) -> int:
        coll_names = self.list_collections()
        n_deletes = 0
        for name in coll_names:
            info = self.client.get_collection(collection_name=name)
            if info.points_count == 0:
                n_deletes += 1
                self.client.delete_collection(collection_name=name)
        return n_deletes

    def list_collections(self) -> List[str]:
        colls = list(self.client.get_collections())[0][1]
        return [coll.name for coll in colls]

    def set_collection(self, collection_name: str) -> None:
        self.config.collection_name = collection_name
        if collection_name not in self.list_collections():
            self.create_collection(collection_name)

    def create_collection(self, collection_name: str) -> None:
        self.config.collection_name = collection_name
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE,
            ),
        )
        collection_info = self.client.get_collection(collection_name=collection_name)
        assert collection_info.status == CollectionStatus.GREEN
        assert collection_info.vectors_count == 0
        if settings.debug:
            level = logger.getEffectiveLevel()
            logger.setLevel(logging.INFO)
            logger.info(collection_info)
            logger.setLevel(level)

    def add_documents(self, documents: List[Document]) -> None:
        embedding_vecs = self.embedding_fn([doc.content for doc in documents])
        if self.config.collection_name is None:
            raise ValueError("No collection name set, cannot ingest docs")
        ids = [self._unique_hash_id(d) for d in documents]
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=Batch(
                ids=ids,  # TODO do we need ids?
                vectors=embedding_vecs,
                payloads=documents,
            ),
        )

    def delete_collection(self, collection_name: str) -> None:
        self.client.delete_collection(collection_name=collection_name)

    def similar_texts_with_scores(
        self,
        text: str,
        k: int = 1,
        where: Optional[str] = None,
    ) -> List[Tuple[Document, float]]:
        embedding = self.embedding_fn([text])[0]
        # TODO filter may not work yet
        filter = Filter() if where is None else Filter.from_json(where)  # type: ignore
        if self.config.collection_name is None:
            raise ValueError("No collection name set, cannot search")
        search_result: List[ScoredPoint] = self.client.search(
            collection_name=self.config.collection_name,
            query_vector=embedding,
            query_filter=filter,
            limit=k,
            search_params=SearchParams(
                hnsw_ef=128,
                exact=False,  # use Apx NN, not exact NN
            ),
        )
        scores = [match.score for match in search_result]
        docs = [
            Document(**(match.payload))  # type: ignore
            for match in search_result
            if match is not None
        ]
        if len(docs) == 0:
            logger.warning(f"No matches found for {text}")
            return []
        if settings.debug:
            logger.info(f"Found {len(docs)} matches, max score: {max(scores)}")
        doc_score_pairs = list(zip(docs, scores))
        self.show_if_debug(doc_score_pairs)
        return doc_score_pairs
