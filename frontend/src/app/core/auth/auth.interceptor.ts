import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandlerFn,
  HttpRequest,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

/**
 * Interceptor HTTP (issue #13): anexa o JWT em todas as chamadas à API via
 * header `Authorization: Bearer <token>`, conforme o backend (`HTTPBearer`).
 *
 * Em erro 401 (token ausente/inválido/expirado) limpa a sessão local para o
 * fluxo de "sessão expirada → volta ao login" (AuthGuard cuida do redirect).
 * O 401 do próprio `POST /api/auth/login` também limpa a sessão — não há o
 * que limpar nesse caso, o erro continua sendo repassado à tela de login.
 */
export function authInterceptor(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
): Observable<HttpEvent<unknown>> {
  const auth = inject(AuthService);

  const token = auth.token;
  if (token !== null) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(req).pipe(
    catchError((erro: HttpErrorResponse) => {
      if (erro.status === 401) {
        auth.limpar();
      }
      return throwError(() => erro);
    }),
  );
}
