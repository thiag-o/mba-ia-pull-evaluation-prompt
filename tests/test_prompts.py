"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    data = load_prompts(PROMPT_FILE)
    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' não encontrado no YAML"
        assert prompt_data["system_prompt"].strip(), "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt_data["system_prompt"]
        assert "Você é um" in system_prompt or "Você é uma" in system_prompt, (
            "O system_prompt não define uma persona com 'Você é um/uma'"
        )

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt_data["system_prompt"]
        format_indicators = ["User Story", "```", "##", "Critérios de Aceitação"]
        assert any(indicator in system_prompt for indicator in format_indicators), (
            "O system_prompt não menciona formato Markdown ou User Story padrão"
        )

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt_data["system_prompt"]
        assert "Exemplo" in system_prompt, "O system_prompt não contém exemplos (Few-shot)"
        assert "Entrada:" in system_prompt, "Os exemplos não possuem campo 'Entrada:'"
        assert "Saída:" in system_prompt, "Os exemplos não possuem campo 'Saída:'"

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        system_prompt = prompt_data["system_prompt"]
        assert "[TODO]" not in system_prompt, "O system_prompt ainda contém marcadores [TODO]"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        tags = prompt_data.get("tags", [])
        assert isinstance(tags, list), "O campo 'tags' deve ser uma lista"
        assert len(tags) >= 2, (
            f"Mínimo de 2 técnicas requeridas em 'tags', encontradas: {len(tags)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
