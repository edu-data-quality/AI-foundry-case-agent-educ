import os

from triagem import http_client, human_review
from triagem.classifier import ErroClassificacao, classificar_solicitacao
from triagem.http_client import ErroChamadaAPI
from triagem.schemas import ResultadoWorkflow
from triagem.validation import EntradaInvalida, validar_entrada

LIMIAR_CONFIANCA = float(os.getenv("TRIAGEM_LIMIAR_CONFIANCA", "0.8"))

ACAO_POR_SETOR = {
    "Financeiro": "gerar_boleto",
    "Academico": "emitir_documento",
}


def _humano(pendencia, resultado: ResultadoWorkflow) -> ResultadoWorkflow:
    resultado.status = "encaminhado_humano"
    resultado.pendencia_id = pendencia.id
    resultado.motivo = pendencia.motivo
    return resultado


def processar(texto_aluno: str, aluno_id: str) -> ResultadoWorkflow:
    resultado = ResultadoWorkflow(status="em_processamento")

    try:
        entrada = validar_entrada(aluno_id, texto_aluno)
    except EntradaInvalida as exc:
        pendencia = human_review.registrar_pendencia(
            "entrada_invalida", str(exc), {"aluno_id": aluno_id}
        )
        return _humano(pendencia, resultado)

    try:
        classificacao = classificar_solicitacao(entrada.texto)
    except ErroClassificacao as exc:
        pendencia = human_review.registrar_pendencia(
            "erro_classificacao", str(exc), {"aluno_id": aluno_id, "texto": entrada.texto}
        )
        return _humano(pendencia, resultado)

    resultado.setor = classificacao.setor
    resultado.urgencia = classificacao.urgencia
    resultado.confianca = classificacao.confianca

    if classificacao.confianca < LIMIAR_CONFIANCA:
        pendencia = human_review.registrar_pendencia(
            "baixa_confianca",
            f"Confiança {classificacao.confianca:.2f} < limiar {LIMIAR_CONFIANCA:.2f}",
            {"aluno_id": aluno_id, "classificacao": classificacao.model_dump()},
        )
        return _humano(pendencia, resultado)

    if classificacao.setor == "Suporte_Geral":
        resultado.status = "direcionado_balcao_geral"
        return resultado

    try:
        resposta_api = http_client.chamar_api_setor(
            classificacao.setor, entrada.aluno_id, classificacao.resumo
        )
    except ErroChamadaAPI as exc:
        pendencia = human_review.registrar_pendencia(
            "erro_api",
            str(exc),
            {"aluno_id": aluno_id, "setor": classificacao.setor, "detalhe": exc.detalhe},
        )
        return _humano(pendencia, resultado)

    resultado.resultado_acao = resposta_api

    if resposta_api.get("requer_aprovacao"):
        pendencia = human_review.registrar_pendencia(
            "acao_sensivel",
            f"Ação sensível requer aprovação: {ACAO_POR_SETOR.get(classificacao.setor)}",
            {
                "aluno_id": entrada.aluno_id,
                "setor": classificacao.setor,
                "acao": ACAO_POR_SETOR.get(classificacao.setor),
            },
        )
        resultado.status = "aguardando_aprovacao"
        resultado.requer_aprovacao = True
        resultado.pendencia_id = pendencia.id
        return resultado

    resultado.status = "concluido"
    return resultado


def decidir_acao_sensivel(pendencia_id: int, aprovado: bool) -> ResultadoWorkflow:
    pendencia = human_review.obter_pendencia(pendencia_id)
    if pendencia is None or pendencia.tipo != "acao_sensivel":
        resultado = ResultadoWorkflow(status="erro")
        resultado.motivo = f"Pendência de ação sensível {pendencia_id} não encontrada"
        return resultado

    if not aprovado:
        human_review.resolver_pendencia(pendencia_id, False)
        resultado = ResultadoWorkflow(status="acao_negada", setor=pendencia.contexto.get("setor"))
        resultado.pendencia_id = pendencia_id
        resultado.motivo = "Ação sensível negada pelo operador"
        return resultado

    try:
        resposta = http_client.executar_acao_sensivel(
            pendencia.contexto["aluno_id"], pendencia.contexto["acao"], True
        )
    except ErroChamadaAPI as exc:
        nova = human_review.registrar_pendencia(
            "erro_acao_sensivel",
            str(exc),
            {"aluno_id": pendencia.contexto["aluno_id"], "detalhe": exc.detalhe},
        )
        resultado = ResultadoWorkflow(status="encaminhado_humano", setor=pendencia.contexto.get("setor"))
        resultado.pendencia_id = nova.id
        resultado.motivo = str(exc)
        return resultado

    human_review.resolver_pendencia(pendencia_id, True)
    resultado = ResultadoWorkflow(status="concluido", setor=pendencia.contexto.get("setor"))
    resultado.pendencia_id = pendencia_id
    resultado.resultado_acao = resposta
    return resultado
