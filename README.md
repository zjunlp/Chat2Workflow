<h1 align="center"> Chat2Workflow </h1>

<div align="center">

[![Awesome](https://awesome.re/badge.svg)](https://github.com/zjunlp/Chat2Workflow) 
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![](https://img.shields.io/github/last-commit/zjunlp/Chat2Workflow?color=green) 

</div>

## Table of Contents
- 👀 [Overview](#overview)
- 🔧 [Installation](#installation)
- 🧐 [Evaluation](#evaluation)
- 💻 [Generation](#generation)

## 👀Overview
![main_picture](./images/main_picture.pdf)

## 🔧Installation
### Conda Environment Configuration
Conda virtual environments offer a light and flexible setup. For different projects, we recommend using separate conda environments for management.

```bash
conda create -n chat2workflow python=3.10
conda activate chat2workflow
pip install -r requirements.txt
```

### Deploy Dify with Docker Compose
> Before installing Dify, make sure your machine meets the following minimum system requirements:
>
> - CPU >= 2 Core
> - RAM >= 4 GiB

</br>

Obtain the specified version of dify:

```bash
git clone https://github.com/langgenius/dify.git --branch 1.9.2 --depth 1
```

The easiest way to start the Dify server is through Docker Compose. Before running Dify with the following commands, make sure that [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) are installed on your machine:

```bash
cd dify
cd docker
cp .env.example .env

# [Optional]: The default port is 80. You can modify it (MY_PORT) here.
# If modified, it needs to be synchronized to `config.yaml`.
perl -pi -e 's/^EXPOSE_NGINX_PORT=.*/EXPOSE_NGINX_PORT={MY_PORT}/' .env

docker compose up -d
```

After running, you can access the Dify dashboard in your browser at http://localhost:{MY_PORT}/install and start the initialization process.


### Dify Initialization
1. Setting up an admin account. Also fill the following information into `config.yaml`.
> - email_address
> - user_name
> - password

</br>

2. Install the following specified version plugins in [Plugins]-[MarketPlace]:
> - langgenius/tongyi:0.1.13 —— API Key Configuration in [Settings]-[WORKSPACE]-[Model Provider]
> - langgenius/openai:0.2.7 —— API Key Configuration in [Settings]-[WORKSPACE]-[Model Provider]
> - wwwzhouhui/qwen_text2image:0.0.3 —— API Key Configuration in [Plugins]
> - langgenius/google:0.0.9 —— API Key Configuration in [Plugins]
> - bowenliang123/md_exporter:2.2.0
> - hjlarry/mermaid_converter:0.0.1
> - langgenius/echarts:0.0.1

</br>

![plugin_version](./images/plugin_version.png)

> In this setup, the LLM defaults to `tongyi:qwen3-vl-plus`, TTS (Text-to-Speech) to `openai:gpt-4o-mini-tts`, image generation to `qwen_text2image:qwen-image`, and search engines to `google:SerpApi`. After the workflow is generated, you can modify the above nodes as needed.

## 🧐Evaluation
1. Fill in the information in the `config.yaml`.

```yaml
# Github REST API for higher rate limits.
# Used for the GithubSummary task in the resolve stage.
github_rest_token: "github_xxx" # null or "github_xxx"

# Your admin account
user_name: "xxx"
email_address: "xxx@yyy.com"
password: "xxxxx"

# LLM API for workflow generation and evaluation
llm_api_key: "sk-xxxxxx"
base_url: "xxxxx"
evaluation_model: deepseek-chat
```

2. Modify the `model_name` and then execute the script sequentially.:
```bash
# Step 1: Generate LLM response.
# The result will be stored in `output/llm_response`.
bash bash_generation.sh

# Step 2: The pass stage of the evaluation.
# The result will be stored in `output/pass_eval` and `output/yaml`.
bash bash_pass_stage.sh

# Step 3: The resolve stage of the evaluation.
# The result will be stored in `output/resolve_eval`.
bash bash_resolve_stage.sh
```

## 💻Generation
1. Fill in the information in the `config.yaml`.
```yaml
# LLM API for workflow generation and evaluation
llm_api_key: "sk-xxxxxx"
base_url: "xxxxx"
```

2. Run the Python script to start the workflow generation program.
```bash
python chat2workflow.py
```
Click on the returned link to start the interactive conversation. 
And import the generated YAML file into the Dify platform for execution.


