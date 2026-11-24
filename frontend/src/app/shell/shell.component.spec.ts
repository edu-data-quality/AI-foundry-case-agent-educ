import { TestBed } from '@angular/core/testing';
import { NavigationEnd, provideRouter, Router } from '@angular/router';
import { first, of } from 'rxjs';

import { ShellComponent } from './shell.component';
import { AuthService } from '../core/auth/auth.service';
import { Role } from '../core/auth/role';

/** Stub mínimo: expõe role e um contador de logout. */
class AuthServiceStub {
  role: Role | null = Role.ALUNO;
  saiu = false;

  logout() {
    this.saiu = true;
    return of(undefined);
  }
}

async function montar(role: Role | null) {
  const auth = new AuthServiceStub();
  auth.role = role;
  await TestBed.configureTestingModule({
    imports: [ShellComponent],
    providers: [
      { provide: AuthService, useValue: auth },
      provideRouter([
        { path: 'aluno', component: ShellComponent },
        { path: 'admin', component: ShellComponent },
        { path: 'login', component: ShellComponent },
      ]),
    ],
  }).compileComponents();
  const fixture = TestBed.createComponent(ShellComponent);
  fixture.detectChanges();
  return { fixture, auth };
}

describe('ShellComponent', () => {
  it('mostra navegação para o chat quando ALUNO', async () => {
    const { fixture } = await montar(Role.ALUNO);
    const texto = fixture.nativeElement.textContent;
    expect(texto).toContain('Chat');
    expect(texto).not.toContain('Painel');
  });

  it('mostra navegação para o painel quando ADMIN', async () => {
    const { fixture } = await montar(Role.ADMIN);
    const texto = fixture.nativeElement.textContent;
    expect(texto).toContain('Painel');
    expect(texto).not.toContain('Chat');
  });

  it('encerra a sessão e volta ao login ao sair', async () => {
    const { fixture, auth } = await montar(Role.ADMIN);
    const router = TestBed.inject(Router);
    const botao = fixture.nativeElement.querySelector('button') as HTMLButtonElement;
    const navegou = new Promise<void>((resolve) => {
      router.events
        .pipe(first((e) => e instanceof NavigationEnd))
        .subscribe(() => resolve());
    });
    botao.click();
    await navegou;

    expect(auth.saiu).toBeTrue();
    expect(router.url).toBe('/login');
  });
});
