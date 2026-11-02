"""Testes do repositório de usuários (controle de acesso aluno/admin)."""

from sqlalchemy.orm import Session

from app.db.models import RoleUsuario
from app.repositories.alunos import AlunoRepository
from app.repositories.usuarios import UsuarioRepository


def test_cria_admin_sem_vinculo_de_aluno(sessao: Session) -> None:
    admin = UsuarioRepository(sessao).criar(
        login="admin", senha_hash="hash", role=RoleUsuario.ADMIN
    )

    assert admin.role is RoleUsuario.ADMIN
    assert admin.aluno_id is None
    assert admin.ativo is True


def test_cria_aluno_vinculado_ao_cadastro(sessao: Session) -> None:
    aluno = AlunoRepository(sessao).criar(
        cpf="12345678901", nome_completo="Maria Souza", email="maria@exemplo.com"
    )

    usuario = UsuarioRepository(sessao).criar(
        login="maria", senha_hash="hash", role=RoleUsuario.ALUNO, aluno_id=aluno.id
    )

    assert usuario.role is RoleUsuario.ALUNO
    assert usuario.aluno is not None
    assert usuario.aluno.cpf == "12345678901"


def test_busca_por_login(sessao: Session) -> None:
    repo = UsuarioRepository(sessao)
    repo.criar(login="admin", senha_hash="hash", role=RoleUsuario.ADMIN)

    assert repo.buscar_por_login("admin").role is RoleUsuario.ADMIN
    assert repo.buscar_por_login("nao-existe") is None
