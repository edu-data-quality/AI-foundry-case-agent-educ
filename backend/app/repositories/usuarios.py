"""Repositório de usuários (controle de acesso)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RoleUsuario, Usuario


class UsuarioRepository:
    """Acesso às credenciais e papéis de aluno/admin."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def criar(
        self,
        *,
        login: str,
        senha_hash: str,
        role: RoleUsuario,
        aluno_id: uuid.UUID | None = None,
        ativo: bool = True,
    ) -> Usuario:
        """Cria e persiste um usuário."""
        usuario = Usuario(
            login=login,
            senha_hash=senha_hash,
            role=role,
            aluno_id=aluno_id,
            ativo=ativo,
        )
        self._sessao.add(usuario)
        self._sessao.commit()
        return usuario

    def buscar_por_login(self, login: str) -> Usuario | None:
        """Busca pelo login informado na autenticação."""
        return self._sessao.scalar(select(Usuario).where(Usuario.login == login))

    def buscar_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        """Busca pelo id interno."""
        return self._sessao.get(Usuario, usuario_id)
