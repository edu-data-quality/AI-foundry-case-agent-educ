import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { Role } from './role';

/**
 * Guard de role (issue #13): exige uma role específica na rota.
 *
 * Sem autenticação delega ao fluxo de login; com a role errada redireciona
 * para a área da própria role (`/aluno` para ALUNO, `/admin` para ADMIN) —
 * "rota admin inacessível para aluno".
 */
export function roleGuard(roleExigida: Role): CanActivateFn {
  return () => {
    const router = inject(Router);
    const auth = inject(AuthService);

    if (!auth.autenticado) {
      return router.createUrlTree(['/login']);
    }
    if (auth.role === roleExigida) {
      return true;
    }
    return router.createUrlTree([auth.role === Role.ALUNO ? '/aluno' : '/admin']);
  };
}
