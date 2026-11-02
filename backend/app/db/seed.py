"""Seed idempotente do ambiente de demonstração.

Cria 1 admin, 1 aluno demo vinculado, disciplinas, matrículas e mensalidades.
Pode rodar quantas vezes for preciso: os registros existentes são preservados.

Uso: `python -m app.db.seed` (após `alembic upgrade head`).
"""

import os
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Aluno,
    Disciplina,
    MatriculaDisciplina,
    Mensalidade,
    RoleUsuario,
    StatusDisciplina,
    StatusPagamento,
    Usuario,
)
from app.db.session import get_session
from app.repositories.academico import DisciplinaRepository, MatriculaRepository
from app.repositories.alunos import AlunoRepository
from app.repositories.financeiro import MensalidadeRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

CPF_ALUNO_DEMO = "11144477735"
EMAIL_ALUNO_DEMO = "aluno.demo@exemplo.com"
LOGIN_ADMIN = "admin"
LOGIN_ALUNO = "aluno"
SENHA_DEMO = "demo1234"
SEMESTRE_LETIVO = "2026.1"
AMBIENTES_BLOQUEADOS = {"production", "prod"}

DISCIPLINAS_DEMO: tuple[tuple[str, str, int], ...] = (
    ("ADS101", "Algoritmos e Lógica de Programação", 1),
    ("ADS102", "Banco de Dados Relacional", 2),
    ("ADS103", "Engenharia de Software", 3),
)


def _aluno_demo(sessao: Session) -> Aluno:
    """Cria o aluno demo se o CPF ainda não existir."""
    repo = AlunoRepository(sessao)
    aluno = repo.buscar_por_cpf(CPF_ALUNO_DEMO)
    if aluno is None:
        aluno = repo.criar(
            cpf=CPF_ALUNO_DEMO,
            nome_completo="Aluno Demonstração",
            email=EMAIL_ALUNO_DEMO,
            telefone="11988887777",
            curso="Análise e Desenvolvimento de Sistemas",
            polo="São Paulo",
        )
    return aluno


def _disciplinas(sessao: Session) -> list[Disciplina]:
    """Cria o catálogo de disciplinas que ainda não existir."""
    repo = DisciplinaRepository(sessao)
    return [
        repo.buscar_por_codigo(codigo)
        or repo.criar(codigo=codigo, nome=nome, semestre_ideal=semestre)
        for codigo, nome, semestre in DISCIPLINAS_DEMO
    ]


def _matriculas(sessao: Session, aluno: Aluno, disciplinas: list[Disciplina]) -> None:
    """Matricula o aluno demo nas disciplinas, se ainda não estiver."""
    repo = MatriculaRepository(sessao)
    existentes = {matricula.disciplina_id for matricula in repo.listar_por_aluno(aluno.id)}
    for indice, disciplina in enumerate(disciplinas):
        if disciplina.id in existentes:
            continue
        if indice == 0:
            repo.criar(
                aluno_id=aluno.id,
                disciplina_id=disciplina.id,
                semestre_letivo=SEMESTRE_LETIVO,
                nota_av1=8.0,
                nota_av2=9.0,
                nota_final=8.5,
                status_disciplina=StatusDisciplina.APROVADO,
            )
        else:
            repo.criar(
                aluno_id=aluno.id,
                disciplina_id=disciplina.id,
                semestre_letivo=SEMESTRE_LETIVO,
                status_disciplina=StatusDisciplina.AGUARDANDO_NOTA,
            )


def _mensalidades(sessao: Session, aluno: Aluno) -> None:
    """Cria mensalidades demo (uma paga, uma pendente), se faltarem."""
    repo = MensalidadeRepository(sessao)
    existentes = {mensalidade.mes_referencia for mensalidade in repo.listar_por_aluno(aluno.id)}
    if "2026-10" not in existentes:
        repo.criar(
            aluno_id=aluno.id,
            mes_referencia="2026-10",
            valor_original=Decimal("450.00"),
            data_vencimento=date(2026, 10, 10),
            status_pagamento=StatusPagamento.PAGO,
        )
    if "2026-11" not in existentes:
        repo.criar(
            aluno_id=aluno.id,
            mes_referencia="2026-11",
            valor_original=Decimal("450.00"),
            data_vencimento=date(2026, 11, 10),
            linha_digitavel="23793.38128 60007.827136 95000.063305 9 00000000045000",
            qr_code_pix="00020126580014BR.GOV.BCB.PIX0136pix-simulado-educ5204000053039865802BR",
        )


def _usuarios(sessao: Session, aluno: Aluno) -> None:
    """Cria o admin e o login do aluno demo, se faltarem."""
    repo = UsuarioRepository(sessao)
    if repo.buscar_por_login(LOGIN_ADMIN) is None:
        repo.criar(
            login=LOGIN_ADMIN,
            senha_hash=hash_senha(SENHA_DEMO),
            role=RoleUsuario.ADMIN,
        )
    if repo.buscar_por_login(LOGIN_ALUNO) is None:
        repo.criar(
            login=LOGIN_ALUNO,
            senha_hash=hash_senha(SENHA_DEMO),
            role=RoleUsuario.ALUNO,
            aluno_id=aluno.id,
        )


def _validar_ambiente() -> None:
    """Bloqueia o seed em produção: os logins demo têm senha pública no repositório."""
    ambiente = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development").lower()
    if ambiente in AMBIENTES_BLOQUEADOS:
        raise RuntimeError(
            f"seed de demonstração bloqueado no ambiente '{ambiente}'"
        )


def executar(sessao: Session) -> dict[str, int]:
    """Aplica o seed e retorna um resumo simples do que existe no banco."""
    _validar_ambiente()
    aluno = _aluno_demo(sessao)
    disciplinas = _disciplinas(sessao)
    _matriculas(sessao, aluno, disciplinas)
    _mensalidades(sessao, aluno)
    _usuarios(sessao, aluno)

    return {
        "alunos": _contar(sessao, Aluno),
        "disciplinas": _contar(sessao, Disciplina),
        "matriculas": _contar(sessao, MatriculaDisciplina),
        "mensalidades": _contar(sessao, Mensalidade),
        "usuarios": _contar(sessao, Usuario),
    }


def _contar(sessao: Session, modelo: type) -> int:
    """Conta as linhas do modelo, para o resumo do seed."""
    return int(sessao.scalar(select(func.count()).select_from(modelo)) or 0)


def main() -> None:
    """Executa o seed e imprime o resumo."""
    with get_session() as sessao:
        resumo = executar(sessao)
    print("Seed aplicado:", ", ".join(f"{chave}={valor}" for chave, valor in resumo.items()))


if __name__ == "__main__":
    main()
