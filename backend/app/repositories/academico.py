"""Repositórios de disciplinas e matrículas."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Disciplina, MatriculaDisciplina, StatusDisciplina


class DisciplinaRepository:
    """Acesso ao catálogo de unidades curriculares."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def criar(self, *, codigo: str, nome: str, semestre_ideal: int) -> Disciplina:
        """Cria e persiste uma disciplina."""
        disciplina = Disciplina(codigo=codigo, nome=nome, semestre_ideal=semestre_ideal)
        self._sessao.add(disciplina)
        self._sessao.commit()
        return disciplina

    def buscar_por_codigo(self, codigo: str) -> Disciplina | None:
        """Busca pelo código da disciplina."""
        return self._sessao.scalar(select(Disciplina).where(Disciplina.codigo == codigo))

    def listar(self) -> list[Disciplina]:
        """Lista o catálogo ordenado por semestre e nome."""
        return list(
            self._sessao.scalars(
                select(Disciplina).order_by(Disciplina.semestre_ideal, Disciplina.nome)
            )
        )


class MatriculaRepository:
    """Acesso ao desempenho do aluno por disciplina."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def criar(
        self,
        *,
        aluno_id: uuid.UUID,
        disciplina_id: uuid.UUID,
        semestre_letivo: str,
        nota_av1: float | None = None,
        nota_av2: float | None = None,
        nota_final: float | None = None,
        status_disciplina: StatusDisciplina = StatusDisciplina.EM_ANDAMENTO,
    ) -> MatriculaDisciplina:
        """Matricula o aluno em uma disciplina."""
        matricula = MatriculaDisciplina(
            aluno_id=aluno_id,
            disciplina_id=disciplina_id,
            semestre_letivo=semestre_letivo,
            nota_av1=nota_av1,
            nota_av2=nota_av2,
            nota_final=nota_final,
            status_disciplina=status_disciplina,
        )
        self._sessao.add(matricula)
        self._sessao.commit()
        return matricula

    def registrar_notas(
        self,
        matricula_id: uuid.UUID,
        *,
        nota_av1: float | None,
        nota_av2: float | None,
        nota_final: float | None,
        status_disciplina: StatusDisciplina,
    ) -> MatriculaDisciplina:
        """Lança as notas e a situação da disciplina."""
        matricula = self._sessao.get(MatriculaDisciplina, matricula_id)
        if matricula is None:
            raise ValueError(f"matrícula {matricula_id} não encontrada")
        matricula.nota_av1 = nota_av1
        matricula.nota_av2 = nota_av2
        matricula.nota_final = nota_final
        matricula.status_disciplina = status_disciplina
        self._sessao.commit()
        return matricula

    def listar_por_aluno(self, aluno_id: uuid.UUID) -> list[MatriculaDisciplina]:
        """Lista as matrículas do aluno com a disciplina carregada."""
        return list(
            self._sessao.scalars(
                select(MatriculaDisciplina)
                .where(MatriculaDisciplina.aluno_id == aluno_id)
                .order_by(MatriculaDisciplina.semestre_letivo)
            )
        )
