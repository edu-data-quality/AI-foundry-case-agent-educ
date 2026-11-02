"""Repositório de alunos."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Aluno, StatusMatricula


class AlunoRepository:
    """Acesso aos dados cadastrais do estudante."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def criar(
        self,
        *,
        cpf: str,
        nome_completo: str,
        email: str,
        telefone: str | None = None,
        curso: str | None = None,
        polo: str | None = None,
        status_matricula: StatusMatricula = StatusMatricula.ATIVO,
    ) -> Aluno:
        """Cria e persiste um aluno."""
        aluno = Aluno(
            cpf=cpf,
            nome_completo=nome_completo,
            email=email,
            telefone=telefone,
            curso=curso,
            polo=polo,
            status_matricula=status_matricula,
        )
        self._sessao.add(aluno)
        self._sessao.commit()
        return aluno

    def buscar_por_id(self, aluno_id: uuid.UUID) -> Aluno | None:
        """Busca pelo id interno."""
        return self._sessao.get(Aluno, aluno_id)

    def buscar_por_cpf(self, cpf: str) -> Aluno | None:
        """Busca pelo CPF, chave de identificação usada pelas tools."""
        return self._sessao.scalar(select(Aluno).where(Aluno.cpf == cpf))
