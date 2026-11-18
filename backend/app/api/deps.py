"""Dependências de autenticação e autorização por role (issue #3).

- `get_usuario_atual`: autentica o Bearer token e retorna o `Usuario`.
- `requer_admin`: exige `role == ADMIN`; aluno autenticado leva 403.

Regra de escopo: endpoints de consulta do aluno retornam apenas os dados do
próprio aluno. O identificador legítimo é o vindo do token
(`usuario.aluno_id` quando `role == ALUNO`) — nunca um CPF vindo do body.
"""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import auth
from app.db.models import RoleUsuario, Usuario
from app.db.session import get_db
from app.repositories.usuarios import UsuarioRepository

_bearer = HTTPBearer(auto_error=False)


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    sessao: Session = Depends(get_db),
) -> Usuario:
    """Autentica o request pelo Bearer token; 401 se ausente ou inválido."""
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token ausente",
        )
    try:
        claims = auth.decodificar_token(credenciais.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth.ERRO_EXPIRADO,
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth.ERRO_INVALIDO,
        ) from exc

    usuario = UsuarioRepository(sessao).buscar_por_id(uuid.UUID(claims["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth.ERRO_INVALIDO,
        )
    return usuario


def requer_admin(
    usuario: Usuario = Depends(get_usuario_atual),
) -> Usuario:
    """Exige role ADMIN; aluno autenticado recebe 403."""
    if usuario.role is not RoleUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso restrito ao administrador",
        )
    return usuario


def aluno_id_do_usuario(usuario: Usuario) -> uuid.UUID | None:
    """`aluno_id` quando o usuário é ALUNO com vínculo; `None` caso contrário.

    ADMIN e ALUNO sem vínculo não têm sessão de chat própria.
    """
    if usuario.role is not RoleUsuario.ALUNO:
        return None
    return usuario.aluno_id


def exigir_aluno(usuario: Usuario) -> uuid.UUID:
    """Retorna o `aluno_id` do usuário ALUNO; 403 para ADMIN ou sem vínculo.

    Usado por rotas que só fazem sentido para o aluno (abrir/fechar/listar a
    própria sessão de chat).
    """
    aluno_id = aluno_id_do_usuario(usuario)
    if aluno_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="apenas o aluno autenticado acessa este recurso",
        )
    return aluno_id


def garantir_acesso_aluno(usuario: Usuario, aluno_id: uuid.UUID) -> None:
    """ADMIN acessa qualquer aluno; ALUNO só o próprio (403 caso contrário)."""
    if usuario.role is RoleUsuario.ADMIN:
        return
    if aluno_id_do_usuario(usuario) != aluno_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso restrito aos próprios dados",
        )