import { Role } from './role';

/**
 * Contrato de `POST /api/auth/login` (backend: `LoginRequest`).
 *
 * `login` é a chave de autenticação (CPF ou usuário cadastrado) e `senha`
 * a senha em texto puro — o transporte é HTTPS.
 */
export interface LoginRequest {
  login: string;
  senha: string;
}

/**
 * Contrato de resposta de `POST /api/auth/login` (backend: `TokenResposta`).
 */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: Role;
  /** Sessão de chat aberta/retomada no login (apenas ALUNO). */
  conversa_id: string | null;
}

/**
 * Perfil do usuário autenticado (backend: `UsuarioAtual`, `GET /api/auth/me`).
 */
export interface UsuarioAtual {
  login: string;
  role: Role;
  aluno_id: string | null;
}
