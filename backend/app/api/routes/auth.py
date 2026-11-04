"""Endpoints de autenticação (issue #3): login e perfil do usuário atual."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth
from app.api.deps import get_usuario_atual
from app.db.models import Usuario
from app.db.session import get_db
from app.repositories.usuarios import UsuarioRepository
from app.security import verificar_senha

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Credenciais enviadas no `POST /api/auth/login`."""

    login: str
    senha: str


class TokenResposta(BaseModel):
    """Token JWT e metadados devolvidos no login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


class UsuarioAtual(BaseModel):
    """Perfil do usuário autenticado (`GET /api/auth/me`)."""

    login: str
    role: str
    aluno_id: str | None = None


@router.post("/login", response_model=TokenResposta, status_code=status.HTTP_200_OK)
def login(payload: LoginRequest, sessao: Session = Depends(get_db)) -> TokenResposta:
    """Autentica login + senha e devolve um JWT.

    Falha com 401 genérico para usuário inexistente, inativo ou senha errada,
    sem revelar qual das causas ocorreu.
    """
    usuario = UsuarioRepository(sessao).buscar_por_login(payload.login)
    if (
        usuario is None
        or not usuario.ativo
        or not verificar_senha(payload.senha, usuario.senha_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciais inválidas",
        )

    token = auth.criar_token(
        usuario_id=str(usuario.id),
        login=usuario.login,
        role=usuario.role.value,
    )
    return TokenResposta(
        access_token=token,
        expires_in=auth.tempo_de_vida_minutos() * 60,
        role=usuario.role.value,
    )


@router.get("/me", response_model=UsuarioAtual)
def me(usuario: Usuario = Depends(get_usuario_atual)) -> UsuarioAtual:
    """Perfil do usuário autenticado — base para o front saber a role."""
    return UsuarioAtual(
        login=usuario.login,
        role=usuario.role.value,
        aluno_id=str(usuario.aluno_id) if usuario.aluno_id else None,
    )