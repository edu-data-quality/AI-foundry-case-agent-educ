import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';

import { AuthService } from './auth.service';
import { authGuard } from './auth.guard';
import { roleGuard } from './role.guard';
import { Role } from './role';

function montarTanque(sessao: unknown): Router {
  TestBed.configureTestingModule({
    imports: [RouterTestingModule],
    providers: [
      {
        provide: AuthService,
        useValue: {
          get autenticado() {
            return (sessao as { autenticado?: boolean } | null)?.autenticado ?? false;
          },
          get role() {
            return (sessao as { role?: Role } | null)?.role ?? null;
          },
        },
      },
    ],
  });
  return TestBed.inject(Router);
}

describe('authGuard', () => {
  it('permite acesso quando autenticado', () => {
    const router = montarTanque({ autenticado: true });
    const resultado = TestBed.runInInjectionContext(() =>
      authGuard({} as never, {} as never),
    );
    expect(resultado).toBeTrue();
    expect(router.url).toBe('');
  });

  it('bloqueia e redireciona para /login quando anônimo', () => {
    const router = montarTanque({ autenticado: false });
    TestBed.runInInjectionContext(() => authGuard({} as never, {} as never));
    expect(router.url).toBe('/login');
  });
});

describe('roleGuard', () => {
  it('permite ALUNO em rota de ALUNO', () => {
    montarTanque({ autenticado: true, role: Role.ALUNO });
    const guard = roleGuard(Role.ALUNO);
    const resultado = TestBed.runInInjectionContext(() =>
      guard({} as never, {} as never),
    );
    expect(resultado).toBeTrue();
  });

  it('redireciona ALUNO para /aluno ao tentar rota ADMIN', () => {
    const router = montarTanque({ autenticado: true, role: Role.ALUNO });
    const guard = roleGuard(Role.ADMIN);
    TestBed.runInInjectionContext(() => guard({} as never, {} as never));
    expect(router.url).toBe('/aluno');
  });

  it('redireciona ADMIN para /admin ao tentar rota ALUNO', () => {
    const router = montarTanque({ autenticado: true, role: Role.ADMIN });
    const guard = roleGuard(Role.ALUNO);
    TestBed.runInInjectionContext(() => guard({} as never, {} as never));
    expect(router.url).toBe('/admin');
  });
});
