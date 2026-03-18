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


def prompt_to_yaml(prompt):
    messages = []

    for msg in prompt.messages:
        role = get_role(msg)

        if hasattr(msg, "prompt") and hasattr(msg.prompt, "template"):
            content = msg.prompt.template
        else:
            content = str(msg)

        messages.append({"role": role, "content": content})

    return {"type": "chat_prompt", "input_variables": prompt.input_variables, "messages": messages}


def pull_prompts_from_langsmith():
    prompt = hub.pull(
        api_key=LANGSMITH_API_KEY,
        api_url=LANGSMITH_ENDPOINT,
        owner_repo_commit="leonanluppi/bug_to_user_story_v1",
    )

    print_section_header("Prompt Pull Successful")

    prompt_dict = prompt_to_yaml(prompt)
    save_yaml(prompt_dict, Path("prompts/prompt.yml"))


def main():
    """Função principal"""

    pull_prompts_from_langsmith()


if __name__ == "__main__":
    sys.exit(main())
