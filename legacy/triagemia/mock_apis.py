from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="APIs Simuladas da Instituição")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALUNOS = {
    "ALU-12345": {
        "nome": "João Silva",
        "curso": "Engenharia de Computação",
        "situacao_matricula": "ativa",
        "inadimplente": False,
        "semestre_atual": 4,
        "coeficiente_rendimento": 7.8,
        "disciplinas": [
            {"codigo": "MAT101", "nome": "Cálculo I", "periodo": "2023.2", "carga_horaria": 80, "nota_final": 8.5, "faltas": 4, "situacao": "Aprovado"},
            {"codigo": "FIS101", "nome": "Física I", "periodo": "2024.1", "carga_horaria": 80, "nota_final": 7.0, "faltas": 8, "situacao": "Aprovado"},
            {"codigo": "CMP201", "nome": "Programação Orientada a Objetos", "periodo": "2024.1", "carga_horaria": 80, "nota_final": 9.2, "faltas": 2, "situacao": "Aprovado"},
            {"codigo": "MAT202", "nome": "Álgebra Linear", "periodo": "2024.2", "carga_horaria": 80, "nota_final": 6.8, "faltas": 10, "situacao": "Aprovado"},
            {"codigo": "EST301", "nome": "Estatística Aplicada", "periodo": "2025.1", "carga_horaria": 60, "nota_final": 8.0, "faltas": 0, "situacao": "Aprovado"},
            {"codigo": "MAT303", "nome": "Cálculo II", "periodo": "2025.1", "carga_horaria": 80, "nota_final": None, "faltas": 3, "situacao": "Em curso"},
        ],
        "historico": [
            {"periodo": "2023.2", "cr": 7.2, "disciplinas_cursadas": 3},
            {"periodo": "2024.1", "cr": 8.0, "disciplinas_cursadas": 4},
            {"periodo": "2024.2", "cr": 7.6, "disciplinas_cursadas": 4},
        ],
    },
    "ALU-99999": {
        "nome": "Maria Souza",
        "curso": "Direito",
        "situacao_matricula": "ativa",
        "inadimplente": True,
        "semestre_atual": 6,
        "coeficiente_rendimento": 8.9,
        "disciplinas": [
            {"codigo": "DIR101", "nome": "Introdução ao Direito", "periodo": "2023.1", "carga_horaria": 60, "nota_final": 9.0, "faltas": 2, "situacao": "Aprovado"},
            {"codigo": "DIR201", "nome": "Direito Civil I", "periodo": "2023.2", "carga_horaria": 80, "nota_final": 8.5, "faltas": 4, "situacao": "Aprovado"},
            {"codigo": "DIR301", "nome": "Direito Constitucional", "periodo": "2024.1", "carga_horaria": 80, "nota_final": 9.5, "faltas": 1, "situacao": "Aprovado"},
            {"codigo": "DIR401", "nome": "Direito Penal I", "periodo": "2024.2", "carga_horaria": 80, "nota_final": 8.0, "faltas": 6, "situacao": "Aprovado"},
            {"codigo": "DIR501", "nome": "Prática Jurídica", "periodo": "2025.1", "carga_horaria": 60, "nota_final": None, "faltas": 0, "situacao": "Em curso"},
        ],
        "historico": [
            {"periodo": "2023.1", "cr": 8.8, "disciplinas_cursadas": 5},
            {"periodo": "2023.2", "cr": 9.1, "disciplinas_cursadas": 5},
            {"periodo": "2024.1", "cr": 9.0, "disciplinas_cursadas": 6},
        ],
    },
    "ALU-88888": {
        "nome": "Pedro Lima",
        "curso": "Medicina",
        "situacao_matricula": "trancada",
        "inadimplente": False,
        "semestre_atual": 2,
        "coeficiente_rendimento": 6.1,
        "disciplinas": [
            {"codigo": "MED101", "nome": "Anatomia Humana", "periodo": "2024.1", "carga_horaria": 120, "nota_final": 4.5, "faltas": 18, "situacao": "Reprovado"},
            {"codigo": "MED102", "nome": "Histologia", "periodo": "2024.1", "carga_horaria": 80, "nota_final": 6.0, "faltas": 12, "situacao": "Aprovado"},
            {"codigo": "MED103", "nome": "Bioquímica", "periodo": "2024.2", "carga_horaria": 80, "nota_final": 7.5, "faltas": 6, "situacao": "Aprovado"},
        ],
        "historico": [
            {"periodo": "2024.1", "cr": 5.3, "disciplinas_cursadas": 2},
            {"periodo": "2024.2", "cr": 7.0, "disciplinas_cursadas": 3},
        ],
    },
}


class SolicitacaoPayload(BaseModel):
    resumo: str
    aluno_id: str = "ALU-12345"


class ConsultaAcademicaPayload(SolicitacaoPayload):
    consulta: str | None = None


class AcaoSensivelPayload(BaseModel):
    aluno_id: str
    acao: str
    aprovado: bool = False


class IdentificacaoPayload(BaseModel):
    aluno_id: str


def _buscar_aluno(aluno_id: str) -> dict:
    if aluno_id.upper().endswith("-ERRO"):
        raise HTTPException(
            status_code=500,
            detail={"status": "erro", "motivo": "falha simulada no sistema de origem"},
        )
    aluno = ALUNOS.get(aluno_id)
    if not aluno:
        raise HTTPException(
            status_code=404,
            detail={"status": "nao_encontrado", "aluno_id": aluno_id},
        )
    return aluno


def _confianca_insuficiente(resumo: str) -> bool:
    return "baixa confiança" in resumo.lower() or "baixa confianca" in resumo.lower()


def _resumo_academico(aluno: dict) -> dict:
    disciplinas = aluno["disciplinas"]
    carga_total = sum(d["carga_horaria"] for d in disciplinas)
    total_faltas = sum(d["faltas"] for d in disciplinas)
    reprovadas = [d["codigo"] for d in disciplinas if d["situacao"] == "Reprovado"]
    return {
        "total_disciplinas": len(disciplinas),
        "total_faltas": total_faltas,
        "carga_horaria_total": carga_total,
        "percentual_faltas": round(total_faltas / carga_total * 100, 1) if carga_total else 0.0,
        "disciplinas_reprovadas": reprovadas,
    }


@app.get("/health", summary="Healthcheck do serviço")
def health():
    return {"status": "ok", "servico": "mock_apis", "alunos_simulados": len(ALUNOS)}


@app.post("/api/aluno", summary="Identifica o aluno pela matrícula")
def api_aluno(payload: IdentificacaoPayload):
    aluno = _buscar_aluno(payload.aluno_id)
    return {
        "status": "sucesso",
        "aluno_id": payload.aluno_id,
        "aluno_nome": aluno["nome"],
        "primeiro_nome": aluno["nome"].split()[0],
        "curso": aluno["curso"],
        "situacao_matricula": aluno["situacao_matricula"],
        "semestre_atual": aluno["semestre_atual"],
    }


@app.post("/api/financeiro", summary="Consulta e processa dados do setor financeiro")
def api_financeiro(payload: SolicitacaoPayload):
    if _confianca_insuficiente(payload.resumo):
        raise HTTPException(
            status_code=422,
            detail={"status": "indefinido", "motivo": "confiança insuficiente; encaminhar para atendimento humano"},
        )

    aluno = _buscar_aluno(payload.aluno_id)
    valor_debito = 450.0 if aluno["inadimplente"] else 0.0

    return {
        "status": "sucesso",
        "setor": "Financeiro",
        "aluno_id": payload.aluno_id,
        "aluno_nome": aluno["nome"],
        "tem_pendencia": valor_debito > 0,
        "valor_debito": valor_debito,
        "meios_pagamento": ["boleto", "pix", "cartao"],
        "acao_realizada": "Boleto 2 via gerado." if valor_debito > 0 else "Nenhum débito encontrado.",
        "requer_aprovacao": valor_debito > 0,
        "detalhes": payload.resumo,
    }


@app.post("/api/academico", summary="Consulta o histórico acadêmico do aluno")
def api_academico(payload: ConsultaAcademicaPayload):
    if _confianca_insuficiente(payload.resumo):
        raise HTTPException(
            status_code=422,
            detail={"status": "indefinido", "motivo": "confiança insuficiente; encaminhar para atendimento humano"},
        )

    aluno = _buscar_aluno(payload.aluno_id)
    elegivel = aluno["situacao_matricula"] == "ativa"
    consulta = (payload.consulta or "completo").lower()

    resposta = {
        "status": "sucesso",
        "setor": "Academico",
        "consulta": consulta,
        "aluno_id": payload.aluno_id,
        "aluno_nome": aluno["nome"],
        "curso": aluno["curso"],
        "situacao_matricula": aluno["situacao_matricula"],
        "semestre_atual": aluno["semestre_atual"],
        "coeficiente_rendimento": aluno["coeficiente_rendimento"],
        "elegivel": elegivel,
        "resumo_academico": _resumo_academico(aluno),
        "documentos_disponiveis": ["historico", "declaracao_matricula", "comprovante_conclusao"],
        "acao_realizada": "Solicitação de documento encaminhada à secretaria." if elegivel else "Aluno não elegível no estado atual.",
        "requer_aprovacao": not elegivel,
        "detalhes": payload.resumo,
    }

    blocos = {
        "notas": "notas",
        "faltas": "faltas",
        "historico": "historico",
        "disciplinas": "disciplinas",
        "completo": "todos",
    }.get(consulta, "todos")

    if blocos in ("todos", "disciplinas", "notas", "faltas"):
        resposta["disciplinas"] = aluno["disciplinas"]
    if blocos in ("todos", "historico"):
        resposta["historico"] = aluno["historico"]

    return resposta


@app.post("/api/acao-sensivel", summary="Executa ação sensível (requer aprovação humana)")
def api_acao_sensivel(payload: AcaoSensivelPayload):
    _buscar_aluno(payload.aluno_id)

    if not payload.aprovado:
        return {
            "status": "negado",
            "aluno_id": payload.aluno_id,
            "acao": payload.acao,
            "requer_aprovacao": False,
            "mensagem": "Ação sensível negada; nada foi executado.",
        }

    return {
        "status": "executado",
        "aluno_id": payload.aluno_id,
        "acao": payload.acao,
        "requer_aprovacao": False,
        "acao_realizada": f"Ação '{payload.acao}' executada com aprovação.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
