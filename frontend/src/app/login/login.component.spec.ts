import { TestBed } from '@angular/core/testing';
import { NavigationEnd, provideRouter, Router } from '@angular/router';
import { first, of, throwError } from 'rxjs';

import { LoginComponent } from './login.component';
import { AuthService } from '../core/auth/auth.service';
import { LoginResponse } from '../core/auth/auth.model';
import { Role } from '../core/auth/role';

/** Stub do serviço de autenticação para isolar a página de login. */
class AuthServiceStub {
  autenticado = false;
  chamada!: { login: string; senha: string };
  resposta: LoginResponse = {
    access_token: 'jwt',
    token_type: 'bearer',
    expires_in: 3600,
    role: Role.ALUNO,
    conversa_id: null,
  };
  falhar = false;

  login(login: string, senha: string) {
    this.chamada = { login, senha };
    if (this.falhar) {
      const erro = new Error('401') as Error & { status?: number };
      erro.status = 401;
      return throwError(() => erro);
    }
    return of(this.resposta);
  }
}

describe('LoginComponent', () => {
  let auth: AuthServiceStub;
  let router: Router;

  beforeEach(async () => {
    auth = new AuthServiceStub();
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: auth },
        provideRouter([
          { path: 'login', component: LoginComponent },
          { path: 'aluno', component: LoginComponent },
          { path: 'admin', component: LoginComponent },
        ]),
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
  });

  function montar() {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    return fixture;
  }

  /** Aguarda a navegação do Router terminar (NavigationEnd). */
  function aguardarNavegacao() {
    return new Promise<void>((resolve) => {
      router.events
        .pipe(first((e) => e instanceof NavigationEnd))
        .subscribe(() => resolve());
    });
  }

  it('deve criar o componente', () => {
    expect(montar().componentInstance).toBeTruthy();
  });

  it('redireciona para a área da role quando já autenticado', async () => {
    auth.autenticado = true;
    auth.resposta.role = Role.ADMIN;
    const navegacao = aguardarNavegacao();
    montar();
    await navegacao;
    expect(router.url).toBe('/admin');
  });

  it('preenche e submete login, chamando authService com as credenciais', () => {
    const fixture = montar();
    const form = fixture.componentInstance.formulario;
    form.setValue({ login: '123.456.789-00', senha: 'segredo' });

    fixture.componentInstance.entrar();
    fixture.detectChanges();

    expect(auth.chamada).toEqual({ login: '123.456.789-00', senha: 'segredo' });
  });

  it('redireciona ALUNO para /aluno após login', async () => {
    auth.resposta.role = Role.ALUNO;
    const navegacao = aguardarNavegacao();
    const fixture = montar();
    fixture.componentInstance.formulario.setValue({ login: 'a', senha: 'b' });
    fixture.componentInstance.entrar();
    fixture.detectChanges();
    await navegacao;

    expect(router.url).toBe('/aluno');
  });

  it('redireciona ADMIN para /admin após login', async () => {
    auth.resposta.role = Role.ADMIN;
    const navegacao = aguardarNavegacao();
    const fixture = montar();
    fixture.componentInstance.formulario.setValue({ login: 'adm', senha: 'x' });
    fixture.componentInstance.entrar();
    fixture.detectChanges();
    await navegacao;

    expect(router.url).toBe('/admin');
  });

  it('mostra erro e não navega quando o backend devolve 401', async () => {
    auth.falhar = true;
    const fixture = montar();
    fixture.componentInstance.formulario.setValue({ login: 'a', senha: 'errada' });
    fixture.componentInstance.entrar();
    await new Promise((r) => setTimeout(r, 0));
    fixture.detectChanges();

    expect(router.url).toBe('/login');
    expect(fixture.componentInstance.erro).toContain('inválidos');
    expect(fixture.nativeElement.textContent).toContain('Login ou senha inválidos');
  });

  it('mantém o botão desabilitado com formulário vazio', () => {
    const fixture = montar();
    const botao: HTMLButtonElement = fixture.nativeElement.querySelector(
      'button[type="submit"]',
    );
    expect(botao.disabled).toBeTrue();
  });
});
