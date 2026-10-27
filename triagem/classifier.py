import os
import re

from openai import AzureOpenAI

from triagem.schemas import ClassificacaoSolicitacao

PROMPT_SISTEMA = (
    "Você é um assistente sênior de triagem de uma secretaria acadêmica. "
    "Classifique a solicitação do aluno de forma precisa, atribuindo um nível de "
    "confiança realista (0 a 1). Use confiança baixa quando o tema for ambíguo."
)


class ErroClassificacao(Exception):
    pass


def _client() -> AzureOpenAI:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not api_key or not endpoint:
        raise ErroClassificacao("AZURE_OPENAI_API_KEY/AZURE_OPENAI_ENDPOINT não configurados")
    return AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)


def _heuristica(texto: str) -> ClassificacaoSolicitacao:
    """Classificador offline para testes sem Azure (definido por palavras-chave)."""
    t = texto.lower()
    termos_fin = ("boleto", "mensalidade", "pagamento", "débito", "debito", "financ", "acordo", "pix")
    termos_acad = ("nota", "falta", "histórico", "historico", "matrícula", "matricula", "disciplina", "diploma", "trancamento")

    pontos_fin = sum(p in t for p in termos_fin)
    pontos_acad = sum(p in t for p in termos_acad)

    if pontos_fin == 0 and pontos_acad == 0:
        return ClassificacaoSolicitacao(
            setor="Suporte_Geral", urgencia="Media", confianca=0.4, resumo=texto[:200]
        )

    setor = "Financeiro" if pontos_fin >= pontos_acad else "Academico"
    confianca = 0.9 if abs(pontos_fin - pontos_acad) >= 1 else 0.6
    urgencia = "Alta" if re.search(r"urgente|hoje|imediato", t) else "Media"
    return ClassificacaoSolicitacao(
        setor=setor, urgencia=urgencia, confianca=confianca, resumo=texto[:200]
    )


def classificar_solicitacao(texto: str, model: str | None = None) -> ClassificacaoSolicitacao:
    if os.getenv("TRIAGEM_OFFLINE") == "1" or not os.getenv("AZURE_OPENAI_API_KEY"):
        return _heuristica(texto)

    deployment = model or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    try:
        response = _client().chat.completions.parse(
            model=deployment,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": texto},
            ],
            response_format=ClassificacaoSolicitacao,
        )
    except Exception as exc:  # noqa: BLE001
        raise ErroClassificacao(f"Falha ao classificar: {exc}") from exc

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ErroClassificacao("Modelo não retornou classificação estruturada")
    return parsed
