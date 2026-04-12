"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header
from pathlib import Path

load_dotenv()

USER = os.getenv("USERNAME_LANGSMITH_HUB")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    ...

    print_section_header("🚀 Fazendo push do prompt para o LangSmith Hub")

    data = prompt_data[prompt_name]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", data["system_prompt"]),
            ("user", data["user_prompt"]),
        ]
    )

    repo = f"{USER}/{prompt_name}"

    hub.push(
        repo_full_name=repo,
        object=prompt,
        tags=data.get("tags"),
    )
    print(f"✅ Prompt publicado com sucesso: {repo}")


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    ...

    errors = []

    if "system_prompt" not in prompt_data:
        errors.append("Campo 'system_prompt' é obrigatório")

    if "user_prompt" not in prompt_data:
        errors.append("Campo 'user_prompt' é obrigatório")

    is_valid = len(errors) == 0

    return is_valid, errors


def main():
    """Função principal"""
    ...

    promptName = "bug_to_user_story_v2"
    yaml = load_yaml(os.path.join(BASE_DIR, "prompts", f"{promptName}.yml"))

    (is_valid, errors) = validate_prompt(yaml.get(promptName))
    if not is_valid:
        print_section_header("❌ Erros de validação encontrados")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    push_prompt_to_langsmith(promptName, yaml)


if __name__ == "__main__":
    sys.exit(main())
