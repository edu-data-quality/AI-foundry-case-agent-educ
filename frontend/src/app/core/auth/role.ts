/**
 * Roles de usuário do portal (espelha o enum `RoleUsuario` do backend).
 *
 * O backend envia a role como string na resposta do login (`role`) e no
 * claim JWT. Valores canônicos: ALUNO e ADMIN.
 */
export type Role = 'ALUNO' | 'ADMIN';

export const Role = {
  ALUNO: 'ALUNO' as Role,
  ADMIN: 'ADMIN' as Role,
};
