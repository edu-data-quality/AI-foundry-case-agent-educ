"""Endpoints de autenticação (issue #3): login e perfil do usuário atual."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth
from app.api.deps import aluno_id_do_usuario, get_usuario_atual
from app.db.models import MotivoFechamento, Usuario
from app.db.session import get_db
from app.repositories.conversas import ConversaRepository
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
    # Sessão de chat aberta/retomada no login (apenas ALUNO).
    conversa_id: str | None = None


class LogoutResposta(BaseModel):
    """Sessão fechada no logout (None quando não havia sessão ABERTA)."""

    conversa_id: str | None = None


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
    conversa_id: str | None = None
    aluno_id = aluno_id_do_usuario(usuario)
    if aluno_id is not None:
        conversa = ConversaRepository(sessao).abrir_ou_continuar(aluno_id)
        conversa_id = str(conversa.id)
    return TokenResposta(
        access_token=token,
        expires_in=auth.tempo_de_vida_minutos() * 60,
        role=usuario.role.value,
        conversa_id=conversa_id,
    )


@router.post("/logout", response_model=LogoutResposta, status_code=status.HTTP_200_OK)
def logout(
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> LogoutResposta:
    """Fecha a sessão ABERTA do aluno com motivo LOGOUT.

    Idempotente: sem sessão ABERTA (ou para ADMIN), devolve `conversa_id`
    nulo. O token continua válido até expirar; o front deve descartá-lo.
    """
    aluno_id = aluno_id_do_usuario(usuario)
    if aluno_id is None:
        return LogoutResposta()

    repo = ConversaRepository(sessao)
    conversa = repo.buscar_aberta_por_aluno(aluno_id)
    if conversa is None:
        return LogoutResposta()
    fechada = repo.fechar(conversa.id, MotivoFechamento.LOGOUT)
    return LogoutResposta(conversa_id=str(fechada.id))


@router.get("/me", response_model=UsuarioAtual)
def me(usuario: Usuario = Depends(get_usuario_atual)) -> UsuarioAtual:
    """Perfil do usuário autenticado — base para o front saber a role."""
    return UsuarioAtual(
        login=usuario.login,
        role=usuario.role.value,
        aluno_id=str(usuario.aluno_id) if usuario.aluno_id else None,
    )