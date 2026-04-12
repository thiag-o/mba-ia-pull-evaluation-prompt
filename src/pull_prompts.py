"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header
from langchain.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
)

load_dotenv()
check_env_vars(["LANGSMITH_API_KEY", "LANGSMITH_ENDPOINT"])


LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT")


def get_role(msg):
    if isinstance(msg, SystemMessagePromptTemplate):
        return "system"
    elif isinstance(msg, HumanMessagePromptTemplate):
        return "user"
    elif isinstance(msg, AIMessagePromptTemplate):
        return "assistant"
    else:
        return "unknown"


def get_prompt_metadata(prompt_identifier):
    client = Client(api_key=LANGSMITH_API_KEY, api_url=LANGSMITH_ENDPOINT)
    return client.get_prompt(prompt_identifier)


def prompt_to_yaml(prompt, prompt_name, metadata=None):
    system_prompt = ""
    user_prompt = ""

    for msg in prompt.messages:
        role = get_role(msg)
        if hasattr(msg, "prompt") and hasattr(msg.prompt, "template"):
            content = msg.prompt.template
        else:
            content = str(msg)

        if role == "system":
            system_prompt = content
        elif role == "user":
            user_prompt = content

    return {
        prompt_name: {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
    }


def pull_prompts_from_langsmith():
    owner_repo_commit = "leonanluppi/bug_to_user_story_v1"
    prompt_name = owner_repo_commit.split("/")[-1].split(":")[0]

    prompt = hub.pull(
        api_key=LANGSMITH_API_KEY,
        api_url=LANGSMITH_ENDPOINT,
        owner_repo_commit=owner_repo_commit,
    )

    metadata = get_prompt_metadata(owner_repo_commit)

    print_section_header("Prompt Pull Successful")

    prompt_dict = prompt_to_yaml(prompt, prompt_name, metadata)
    save_yaml(prompt_dict, Path(f"prompts/{prompt_name}.yml"))


def main():
    """Função principal"""

    pull_prompts_from_langsmith()


if __name__ == "__main__":
    sys.exit(main())
