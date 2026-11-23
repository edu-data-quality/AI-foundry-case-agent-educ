import { inject } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  CanActivateFn,
  Router,
  RouterStateSnapshot,
} from '@angular/router';

import { AuthService } from './auth.service';

/**
 * Guard de autenticação (issue #13): permite a rota apenas com sessão ativa;
 * caso contrário redireciona para `/login`.
 */
export const authGuard: CanActivateFn = (
  _route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot,
) => {
  const router = inject(Router);
  const auth = inject(AuthService);

  if (auth.autenticado) {
    return true;
  }

  return router.createUrlTree(['/login'], {
    queryParams: { destino: state.url },
  });
};
