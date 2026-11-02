"""Testes do repositório de alunos."""

from sqlalchemy.orm import Session

from app.db.models import StatusMatricula
from app.repositories.alunos import AlunoRepository


def _criar_aluno(sessao: Session, cpf: str = "12345678901"):
    return AlunoRepository(sessao).criar(
        cpf=cpf,
        nome_completo="Maria Souza",
        email="maria@exemplo.com",
        telefone="11999990000",
        curso="Análise e Desenvolvimento de Sistemas",
        polo="São Paulo",
    )


def test_cria_aluno_com_status_ativo_por_padrao(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)

    assert aluno.id is not None
    assert aluno.status_matricula is StatusMatricula.ATIVO


def test_busca_aluno_por_cpf(sessao: Session) -> None:
    criado = _criar_aluno(sessao)
    repo = AlunoRepository(sessao)

    assert repo.buscar_por_cpf("12345678901").id == criado.id
    assert repo.buscar_por_cpf("00000000000") is None


def test_busca_aluno_por_id(sessao: Session) -> None:
    criado = _criar_aluno(sessao)
    repo = AlunoRepository(sessao)

    assert repo.buscar_por_id(criado.id).nome_completo == "Maria Souza"
