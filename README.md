# llmagent

<!--
Fix these badge links later

[![Documentation](https://readthedocs.org/projects/project-name/badge/)](https://project-name.readthedocs.io/)

[![Build Status](https://github.com/username/repository-name/actions/workflows/workflow-name.yml/badge.svg)](https://github.com/username/repository-name/actions)

[![codecov](https://codecov.io/gh/username/repository-name/branch/main/graph/badge.svg)](https://codecov.io/gh/username/repository-name)

[![License](https://img.shields.io/github/license/username/repository-name)](https://github.com/username/repository-name/blob/main/LICENSE)

-->

[![Deploy MkDocs to Pages](https://github.com/langroid/llmagent/actions/workflows/mkdocs-deploy.yml/badge.svg)](https://github.com/langroid/llmagent/actions/workflows/mkdocs-deploy.yml)

### Set up dev env

First install `poetry`, then create virtual env and install dependencies:

```bash
# clone the repo and cd into repo root
git clone ...
cd llmagent

# create a virtual env under project root, .venv directory
python3 -m venv .venv

# activate the virtual env
. .venv/bin/activate

# use poetry to install dependencies (these go into .venv dir)
poetry install
```
Copy the `.env-template` file to `.env` and insert your OpenAI API key.
Currently only OpenAI models are supported. Others will be added later.



### Run some examples

1. "Chat" with a set of URLs. 
```bash
python3 examples/urlqa/chat.py
```

To see more output, run with `debug=True`:
```bash
python3 examples/urlqa/chat.py debug=True
```

Ask a question you want answered based on the URLs content. The default 
URLs are about various articles and discussions on LLM-based agents, 
compression and intelligence. Try asking:
> who is Pattie Maes?





