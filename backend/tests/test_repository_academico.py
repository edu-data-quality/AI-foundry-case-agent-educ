"""Testes dos repositórios de disciplinas, matrículas e documentos."""

from sqlalchemy.orm import Session

from app.db.models import StatusDisciplina
from app.repositories.academico import DisciplinaRepository, MatriculaRepository
from app.repositories.alunos import AlunoRepository
from app.repositories.documentos import SolicitacaoDocumentoRepository


def _aluno(sessao: Session):
    return AlunoRepository(sessao).criar(
        cpf="12345678901", nome_completo="Maria Souza", email="maria@exemplo.com"
    )


def _disciplina(sessao: Session, codigo: str = "ADS101"):
    return DisciplinaRepository(sessao).criar(
        codigo=codigo, nome="Programação I", semestre_ideal=1
    )


def test_busca_disciplina_por_codigo(sessao: Session) -> None:
    disciplina = _disciplina(sessao)
    repo = DisciplinaRepository(sessao)

    assert repo.buscar_por_codigo("ADS101").id == disciplina.id
    assert repo.buscar_por_codigo("XPTO") is None


def test_matricula_comeca_em_andamento_sem_notas(sessao: Session) -> None:
    aluno = _aluno(sessao)
    disciplina = _disciplina(sessao)

    matricula = MatriculaRepository(sessao).criar(
        aluno_id=aluno.id, disciplina_id=disciplina.id, semestre_letivo="2026.1"
    )

    assert matricula.status_disciplina is StatusDisciplina.EM_ANDAMENTO
    assert matricula.nota_av1 is None
    assert matricula.nota_final is None


def test_lista_matriculas_do_aluno_com_disciplina(sessao: Session) -> None:
    aluno = _aluno(sessao)
    disciplina = _disciplina(sessao)
    repo = MatriculaRepository(sessao)
    repo.criar(aluno_id=aluno.id, disciplina_id=disciplina.id, semestre_letivo="2026.1")

    matriculas = repo.listar_por_aluno(aluno.id)

    assert len(matriculas) == 1
    assert matriculas[0].disciplina.codigo == "ADS101"


def test_registra_lancamento_de_nota(sessao: Session) -> None:
    aluno = _aluno(sessao)
    disciplina = _disciplina(sessao)
    repo = MatriculaRepository(sessao)
    matricula = repo.criar(
        aluno_id=aluno.id, disciplina_id=disciplina.id, semestre_letivo="2026.1"
    )

    atualizada = repo.registrar_notas(
        matricula.id,
        nota_av1=8.0,
        nota_av2=9.0,
        nota_final=8.5,
        status_disciplina=StatusDisciplina.APROVADO,
    )

    assert atualizada.nota_final == 8.5
    assert atualizada.status_disciplina is StatusDisciplina.APROVADO


def test_registra_solicitacao_de_documento_com_data(sessao: Session) -> None:
    aluno = _aluno(sessao)
    repo = SolicitacaoDocumentoRepository(sessao)

    solicitacao = repo.registrar(
        aluno_id=aluno.id, tipo_documento="matricula", enviado_para_email=aluno.email
    )

    assert solicitacao.data_emissao is not None
    assert repo.listar_por_aluno(aluno.id)[0].tipo_documento == "matricula"
