import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { SessaoAlunoService } from '../services/sessao-aluno.service';

/**
 * Interceptor que injeta `Authorization: Bearer <token>` nas chamadas à API.
 *
 * MOCK PROVISÓRIO do #15: lê o token do `SessaoAlunoService`, que hoje é o
 * `MockSessaoAlunoService`. Quando o interceptor/guard do #13 (app shell)
 * existir na base, substituir por ele e remover este arquivo.
 */
export const authMockInterceptor: HttpInterceptorFn = (req, next) => {
  const sessao = inject(SessaoAlunoService);
  if (sessao.token) {
    const autenticada = req.clone({
      setHeaders: { Authorization: `Bearer ${sessao.token}` },
    });
    return next(autenticada);
  }
  return next(req);
};
