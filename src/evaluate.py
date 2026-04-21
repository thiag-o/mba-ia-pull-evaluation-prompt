"""
Script COMPLETO para avaliar prompts otimizados.

Este script:
1. Carrega dataset de avaliação de arquivo .jsonl (datasets/bug_to_user_story.jsonl)
2. Cria/atualiza dataset no LangSmith
3. Puxa prompts otimizados do LangSmith Hub (fonte única de verdade)
4. Executa prompts contra o dataset usando langsmith.evaluate()
5. Calcula 5 métricas (Helpfulness, Correctness, F1-Score, Clarity, Precision)
6. Publica resultados no dashboard do LangSmith como Experiment (tabela de métricas)
7. Exibe resumo no terminal

Suporta múltiplos providers de LLM:
- OpenAI (gpt-4o, gpt-4o-mini)
- Google Gemini (gemini-1.5-flash, gemini-1.5-pro)

Configure o provider no arquivo .env através da variável LLM_PROVIDER.
"""

import os
import sys
import json
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client, evaluate
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import check_env_vars, format_score, print_section_header, get_llm as get_configured_llm
from metrics import evaluate_f1_score, evaluate_clarity, evaluate_precision

load_dotenv()


def get_llm():
    return get_configured_llm(temperature=0)


def load_dataset_from_jsonl(jsonl_path: str) -> List[Dict[str, Any]]:
    examples = []

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    example = json.loads(line)
                    examples.append(example)

        return examples

    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {jsonl_path}")
        print("\nCertifique-se de que o arquivo datasets/bug_to_user_story.jsonl existe.")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao parsear JSONL: {e}")
        return []
    except Exception as e:
        print(f"❌ Erro ao carregar dataset: {e}")
        return []


def create_evaluation_dataset(client: Client, dataset_name: str, jsonl_path: str) -> str:
    print(f"Criando dataset de avaliação: {dataset_name}...")

    examples = load_dataset_from_jsonl(jsonl_path)

    if not examples:
        print("❌ Nenhum exemplo carregado do arquivo .jsonl")
        return dataset_name

    print(f"   ✓ Carregados {len(examples)} exemplos do arquivo {jsonl_path}")

    try:
        datasets = client.list_datasets(dataset_name=dataset_name)
        existing_dataset = None

        for ds in datasets:
            if ds.name == dataset_name:
                existing_dataset = ds
                break

        if existing_dataset:
            print(f"   ✓ Dataset '{dataset_name}' já existe, usando existente")
            return dataset_name
        else:
            dataset = client.create_dataset(dataset_name=dataset_name)

            for example in examples:
                client.create_example(
                    dataset_id=dataset.id, inputs=example["inputs"], outputs=example["outputs"]
                )

            print(f"   ✓ Dataset criado com {len(examples)} exemplos")
            return dataset_name

    except Exception as e:
        print(f"   ⚠️  Erro ao criar dataset: {e}")
        return dataset_name


def pull_prompt_from_langsmith(prompt_name: str) -> ChatPromptTemplate:
    try:
        print(f"   Puxando prompt do LangSmith Hub: {prompt_name}")
        prompt = hub.pull(prompt_name)
        print(f"   ✓ Prompt carregado com sucesso")
        return prompt

    except Exception as e:
        error_msg = str(e).lower()

        print(f"\n{'=' * 70}")
        print(f"❌ ERRO: Não foi possível carregar o prompt '{prompt_name}'")
        print(f"{'=' * 70}\n")

        if "not found" in error_msg or "404" in error_msg:
            print("⚠️  O prompt não foi encontrado no LangSmith Hub.\n")
            print("AÇÕES NECESSÁRIAS:")
            print("1. Verifique se você já fez push do prompt otimizado:")
            print(f"   python src/push_prompts.py")
            print()
            print("2. Confirme se o prompt foi publicado com sucesso em:")
            print(f"   https://smith.langchain.com/prompts")
            print()
            print(f"3. Certifique-se de que o nome do prompt está correto: '{prompt_name}'")
            print()
            print("4. Se você alterou o prompt no YAML, refaça o push:")
            print(f"   python src/push_prompts.py")
        else:
            print(f"Erro técnico: {e}\n")
            print("Verifique:")
            print("- LANGSMITH_API_KEY está configurada corretamente no .env")
            print("- Você tem acesso ao workspace do LangSmith")
            print("- Sua conexão com a internet está funcionando")

        print(f"\n{'=' * 70}\n")
        raise


def build_target_fn(prompt_template: ChatPromptTemplate):
    """
    Retorna uma função target compatível com langsmith.evaluate().
    Recebe inputs do dataset e retorna o output gerado pelo prompt.
    """
    llm = get_llm()
    chain = prompt_template | llm

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        response = chain.invoke(inputs)
        return {"answer": response.content}

    return target


def make_f1_evaluator():
    def evaluator(
        inputs: Dict[str, Any], outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        question = inputs.get("question", inputs.get("bug_report", inputs.get("pr_title", "")))
        answer = outputs.get("answer", "")
        reference = reference_outputs.get("reference", "")

        result = evaluate_f1_score(question, answer, reference)
        return {"key": "f1_score", "score": result["score"]}

    evaluator.__name__ = "f1_score"
    return evaluator


def make_clarity_evaluator():
    def evaluator(
        inputs: Dict[str, Any], outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        question = inputs.get("question", inputs.get("bug_report", inputs.get("pr_title", "")))
        answer = outputs.get("answer", "")
        reference = reference_outputs.get("reference", "")

        result = evaluate_clarity(question, answer, reference)
        return {"key": "clarity", "score": result["score"]}

    evaluator.__name__ = "clarity"
    return evaluator


def make_precision_evaluator():
    def evaluator(
        inputs: Dict[str, Any], outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        question = inputs.get("question", inputs.get("bug_report", inputs.get("pr_title", "")))
        answer = outputs.get("answer", "")
        reference = reference_outputs.get("reference", "")

        result = evaluate_precision(question, answer, reference)
        return {"key": "precision", "score": result["score"]}

    evaluator.__name__ = "precision"
    return evaluator


def make_helpfulness_evaluator():
    def evaluator(
        inputs: Dict[str, Any], outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        question = inputs.get("question", inputs.get("bug_report", inputs.get("pr_title", "")))
        answer = outputs.get("answer", "")
        reference = reference_outputs.get("reference", "")

        clarity = evaluate_clarity(question, answer, reference)
        precision = evaluate_precision(question, answer, reference)
        helpfulness = (clarity["score"] + precision["score"]) / 2
        return {"key": "helpfulness", "score": round(helpfulness, 4)}

    evaluator.__name__ = "helpfulness"
    return evaluator


def make_correctness_evaluator():
    def evaluator(
        inputs: Dict[str, Any], outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        question = inputs.get("question", inputs.get("bug_report", inputs.get("pr_title", "")))
        answer = outputs.get("answer", "")
        reference = reference_outputs.get("reference", "")

        f1 = evaluate_f1_score(question, answer, reference)
        precision = evaluate_precision(question, answer, reference)
        correctness = (f1["score"] + precision["score"]) / 2
        return {"key": "correctness", "score": round(correctness, 4)}

    evaluator.__name__ = "correctness"
    return evaluator


def run_experiment(prompt_name: str, dataset_name: str, project_name: str) -> Dict[str, float]:
    print(f"\n🔍 Iniciando experimento para: {prompt_name}")

    prompt_template = pull_prompt_from_langsmith(prompt_name)
    target_fn = build_target_fn(prompt_template)

    evaluators = [
        make_f1_evaluator(),
        make_clarity_evaluator(),
        make_precision_evaluator(),
        make_helpfulness_evaluator(),
        make_correctness_evaluator(),
    ]

    print(f"   Executando evaluate() contra dataset '{dataset_name}'...")
    print(f"   Os resultados serão publicados como Experiment no LangSmith.\n")

    results = evaluate(
        target_fn,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=prompt_name,
        max_concurrency=1,
        metadata={"prompt_name": prompt_name, "project": project_name},
    )

    scores: Dict[str, List[float]] = {
        "helpfulness": [],
        "correctness": [],
        "f1_score": [],
        "clarity": [],
        "precision": [],
    }

    for result in results:
        eval_results = result.get("evaluation_results", {}).get("results", [])
        for er in eval_results:
            key = er.key
            if key in scores and er.score is not None:
                scores[key].append(er.score)

    avg_scores = {k: round(sum(v) / len(v), 4) if v else 0.0 for k, v in scores.items()}

    return avg_scores


def display_results(prompt_name: str, scores: Dict[str, float]) -> bool:
    print("\n" + "=" * 50)
    print(f"Prompt: {prompt_name}")
    print("=" * 50)

    print("\nMétricas LangSmith:")
    print(f"  - Helpfulness: {format_score(scores['helpfulness'], threshold=0.9)}")
    print(f"  - Correctness: {format_score(scores['correctness'], threshold=0.9)}")

    print("\nMétricas Customizadas:")
    print(f"  - F1-Score: {format_score(scores['f1_score'], threshold=0.9)}")
    print(f"  - Clarity: {format_score(scores['clarity'], threshold=0.9)}")
    print(f"  - Precision: {format_score(scores['precision'], threshold=0.9)}")

    average_score = sum(scores.values()) / len(scores)

    print("\n" + "-" * 50)
    print(f"📊 MÉDIA GERAL: {average_score:.4f}")
    print("-" * 50)

    passed = average_score >= 0.9

    if passed:
        print(f"\n✅ STATUS: APROVADO (média >= 0.9)")
    else:
        print(f"\n❌ STATUS: REPROVADO (média < 0.9)")
        print(f"⚠️  Média atual: {average_score:.4f} | Necessário: 0.9000")

    return passed


def main():
    print_section_header("AVALIAÇÃO DE PROMPTS OTIMIZADOS")

    provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    eval_model = os.getenv("EVAL_MODEL", "gpt-4o")

    print(f"Provider: {provider}")
    print(f"Modelo Principal: {llm_model}")
    print(f"Modelo de Avaliação: {eval_model}\n")

    required_vars = ["LANGSMITH_API_KEY", "LLM_PROVIDER"]
    if provider == "openai":
        required_vars.append("OPENAI_API_KEY")
    elif provider in ["google", "gemini"]:
        required_vars.append("GOOGLE_API_KEY")

    if not check_env_vars(required_vars):
        return 1

    client = Client()
    project_name = os.getenv("LANGCHAIN_PROJECT", "prompt-optimization-challenge-resolved")

    jsonl_path = "datasets/bug_to_user_story.jsonl"

    if not Path(jsonl_path).exists():
        print(f"❌ Arquivo de dataset não encontrado: {jsonl_path}")
        print("\nCertifique-se de que o arquivo existe antes de continuar.")
        return 1

    dataset_name = f"{project_name}-eval"
    create_evaluation_dataset(client, dataset_name, jsonl_path)

    print("\n" + "=" * 70)
    print("PROMPTS PARA AVALIAR")
    print("=" * 70)
    print("\nEste script irá puxar prompts do LangSmith Hub.")
    print("Certifique-se de ter feito push dos prompts antes de avaliar:")
    print("  python src/push_prompts.py\n")

    prompts_to_evaluate = [
        "bug_to_user_story_v2",
    ]

    all_passed = True
    evaluated_count = 0
    results_summary = []

    for prompt_name in prompts_to_evaluate:
        evaluated_count += 1

        try:
            scores = run_experiment(prompt_name, dataset_name, project_name)

            passed = display_results(prompt_name, scores)
            all_passed = all_passed and passed

            results_summary.append({"prompt": prompt_name, "scores": scores, "passed": passed})

        except Exception as e:
            print(f"\n❌ Falha ao avaliar '{prompt_name}': {e}")
            all_passed = False

            results_summary.append(
                {
                    "prompt": prompt_name,
                    "scores": {
                        "helpfulness": 0.0,
                        "correctness": 0.0,
                        "f1_score": 0.0,
                        "clarity": 0.0,
                        "precision": 0.0,
                    },
                    "passed": False,
                }
            )

    print("\n" + "=" * 50)
    print("RESUMO FINAL")
    print("=" * 50 + "\n")

    if evaluated_count == 0:
        print("⚠️  Nenhum prompt foi avaliado")
        return 1

    print(f"Prompts avaliados: {evaluated_count}")
    print(f"Aprovados: {sum(1 for r in results_summary if r['passed'])}")
    print(f"Reprovados: {sum(1 for r in results_summary if not r['passed'])}\n")

    if all_passed:
        print("✅ Todos os prompts atingiram média >= 0.9!")
        print(f"\n✓ Confira os resultados (tabela de métricas) em:")
        print(
            f"  https://smith.langchain.com/o/default/datasets/{dataset_name.replace(' ', '%20')}"
        )
        print(f"\n✓ Ou acesse o projeto:")
        print(f"  https://smith.langchain.com/projects/{project_name}")
        print("\nPróximos passos:")
        print("1. Documente o processo no README.md")
        print("2. Capture screenshots das avaliações")
        print("3. Faça commit e push para o GitHub")
        return 0
    else:
        print("⚠️  Alguns prompts não atingiram média >= 0.9")
        print("\nPróximos passos:")
        print("1. Refatore os prompts com score baixo")
        print("2. Faça push novamente: python src/push_prompts.py")
        print("3. Execute: python src/evaluate.py novamente")
        return 1


if __name__ == "__main__":
    sys.exit(main())
