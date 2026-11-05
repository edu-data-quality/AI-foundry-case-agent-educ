"""Status académico do aluno (issue #4 / US1.2 do PRD).

Regra de escopo:
- `ALUNO` consulta apenas o próprio CPF; outro CPF recebe 403.
- `ADMIN` consulta qualquer CPF (painel administrativo e tools do Foundry).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.db.models import RoleUsuario, StatusDisciplina, StatusMatricula, Usuario
from app.db.session import get_db
from app.repositories.academico import MatriculaRepository
from app.repositories.alunos import AlunoRepository

router = APIRouter(prefix="/api/aluno", tags=["aluno"])


class DadosAluno(BaseModel):
    """Dados cadastrais básicos exibidos junto ao status académico."""

    id: str
    cpf: str
    nome_completo: str
    email: str
    curso: str | None = None
    polo: str | None = None
    status_matricula: StatusMatricula


class DisciplinaStatus(BaseModel):
    """Notas e situação do aluno em uma disciplina."""

    disciplina_id: str
    codigo: str
    nome: str
    semestre_letivo: str
    nota_av1: float | None = None
    nota_av2: float | None = None
    nota_final: float | None = None
    status_disciplina: StatusDisciplina


class StatusAcademicoResposta(BaseModel):
    """Contrato do `GET /api/aluno/status` (mapeado como tool no Foundry)."""

    aluno: DadosAluno
    disciplinas: list[DisciplinaStatus]


def _resolver_aluno(usuario: Usuario, cpf: str, sessao: Session):
    """Resolve o aluno do request respeitando o escopo da role.

    Para `ALUNO`, a identidade vem do token (`usuario.aluno`), nunca do CPF
    consultado; CPF diferente do próprio é tratado como acesso negado.
    """
    if usuario.role is RoleUsuario.ALUNO:
        aluno = usuario.aluno
        if aluno is None or aluno.cpf != cpf:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="acesso restrito aos próprios dados",
            )
        return aluno

    aluno = AlunoRepository(sessao).buscar_por_cpf(cpf)
    if aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aluno não encontrado",
        )
    return aluno


@router.get(
    "/status",
    response_model=StatusAcademicoResposta,
    responses={
        403: {"description": "Aluno autenticado consultando CPF de outro aluno"},
        404: {"description": "CPF não cadastrado"},
    },
)
def status_academico(
    cpf: str = Query(
        ...,
        pattern=r"^\d{11}$",
        description="CPF do aluno, apenas dígitos (11 caracteres)",
    ),
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> StatusAcademicoResposta:
    """Retorna dados do aluno e notas/situação por disciplina.

    Erros: 401 sem token válido, 403 para aluno consultando outro CPF,
    404 para CPF inexistente (quando quem consulta é ADMIN).
    """
    aluno = _resolver_aluno(usuario, cpf, sessao)
    matriculas = MatriculaRepository(sessao).listar_por_aluno(aluno.id)

    return StatusAcademicoResposta(
        aluno=DadosAluno(
            id=str(aluno.id),
            cpf=aluno.cpf,
            nome_completo=aluno.nome_completo,
            email=aluno.email,
            curso=aluno.curso,
            polo=aluno.polo,
            status_matricula=aluno.status_matricula,
        ),
        disciplinas=[
            DisciplinaStatus(
                disciplina_id=str(matricula.disciplina_id),
                codigo=matricula.disciplina.codigo,
                nome=matricula.disciplina.nome,
                semestre_letivo=matricula.semestre_letivo,
                nota_av1=matricula.nota_av1,
                nota_av2=matricula.nota_av2,
                nota_final=matricula.nota_final,
                status_disciplina=matricula.status_disciplina,
            )
            for matricula in matriculas
        ],
    )
