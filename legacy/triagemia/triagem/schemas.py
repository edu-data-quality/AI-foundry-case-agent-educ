from typing import Literal

from pydantic import BaseModel, Field


class EntradaAluno(BaseModel):
    aluno_id: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9\-]+$",
        description="Identificador do aluno.",
    )
    texto: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Texto da solicitação já sanitizado.",
    )


class ClassificacaoSolicitacao(BaseModel):
    setor: Literal["Financeiro", "Academico", "Suporte_Geral"] = Field(
        description="Setor de destino com base no conteúdo da solicitação."
    )
    urgencia: Literal["Baixa", "Media", "Alta"] = Field(
        description="Nível de urgência avaliado."
    )
    confianca: float = Field(
        ge=0.0,
        le=1.0,
        description="Grau de confiança da IA na classificação, de 0 a 1.",
    )
    resumo: str = Field(description="Resumo executivo do problema do aluno.")


class ResultadoWorkflow(BaseModel):
    status: str
    setor: str | None = None
    urgencia: str | None = None
    confianca: float | None = None
    pendencia_id: int | None = None
    requer_aprovacao: bool = False
    resultado_acao: dict | None = None
    motivo: str | None = None
