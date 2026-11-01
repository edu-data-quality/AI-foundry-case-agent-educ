import os

import requests

BASE_URL = os.getenv("MOCK_API_URL", "http://127.0.0.1:8000")
TIMEOUT = float(os.getenv("MOCK_API_TIMEOUT", "10"))

ROTAS = {
    "Financeiro": "/api/financeiro",
    "Academico": "/api/academico",
}
ROTA_ACAO_SENSIVEL = "/api/acao-sensivel"


class ErroChamadaAPI(Exception):
    def __init__(self, mensagem: str, status_code: int | None = None, detalhe: dict | None = None):
        super().__init__(mensagem)
        self.status_code = status_code
        self.detalhe = detalhe or {}


def _post(rota: str, payload: dict) -> dict:
    url = f"{BASE_URL}{rota}"
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ErroChamadaAPI(f"API indisponível em {url}: {exc}") from exc

    if response.status_code >= 500:
        raise ErroChamadaAPI("Erro no sistema de origem", response.status_code, _json(response))
    if response.status_code == 404:
        raise ErroChamadaAPI("Aluno não encontrado", 404, _json(response))
    if response.status_code >= 400:
        raise ErroChamadaAPI(f"Requisição rejeitada ({response.status_code})", response.status_code, _json(response))
    return response.json()


def _json(response: requests.Response) -> dict:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:500]}


def chamar_api_setor(setor: str, aluno_id: str, resumo: str) -> dict:
    rota = ROTAS.get(setor)
    if not rota:
        raise ErroChamadaAPI(f"Sem API para o setor '{setor}'")
    return _post(rota, {"aluno_id": aluno_id, "resumo": resumo})


def executar_acao_sensivel(aluno_id: str, acao: str, aprovado: bool) -> dict:
    return _post(ROTA_ACAO_SENSIVEL, {"aluno_id": aluno_id, "acao": acao, "aprovado": aprovado})
