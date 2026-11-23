import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';
import { LoginResponse } from './auth.model';
import { Role } from './role';

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;
  const urlLogin = `${environment.apiUrl}/api/auth/login`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [provideHttpClient(), AuthService],
    });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('deve fazer POST /api/auth/login com login e senha', () => {
    let resposta: LoginResponse | undefined;
    service.login('123.456.789-00', 'segredo').subscribe((r) => (resposta = r));

    const req = http.expectOne(urlLogin);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      login: '123.456.789-00',
      senha: 'segredo',
    });

    req.flush({
      access_token: 'jwt-token',
      token_type: 'bearer',
      expires_in: 3600,
      role: 'ALUNO',
      conversa_id: 'conv-1',
    } satisfies LoginResponse);

    expect(resposta?.access_token).toBe('jwt-token');
    expect(resposta?.role).toBe(Role.ALUNO);
  });

  it('deve guardar token, role e conversa_id após login', () => {
    service.login('aluno', 'senha').subscribe();

    const req = http.expectOne(urlLogin);
    req.flush({
      access_token: 'jwt-token',
      token_type: 'bearer',
      expires_in: 60,
      role: 'ADMIN',
      conversa_id: null,
    } satisfies LoginResponse);

    expect(service.token).toBe('jwt-token');
    expect(service.role).toBe(Role.ADMIN);
    expect(service.autenticado).toBeTrue();
    expect(service.conversaId).toBeNull();
  });

  it('deve propagar erro 401 de credenciais inválidas', () => {
    let erro: unknown;
    service.login('x', 'y').subscribe({
      error: (e) => (erro = e),
    });

    const req = http.expectOne(urlLogin);
    req.flush(
      { detail: 'credenciais inválidas' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(erro).toBeTruthy();
    expect(service.autenticado).toBeFalse();
  });

  it('logout deve fazer POST /api/auth/logout e limpar a sessão', () => {
    service.login('a', 'b').subscribe();
    http.expectOne(urlLogin).flush({
      access_token: 't',
      token_type: 'bearer',
      expires_in: 60,
      role: 'ALUNO',
      conversa_id: 'c1',
    } satisfies LoginResponse);

    let feito = false;
    service.logout().subscribe(() => (feito = true));

    const req = http.expectOne(`${environment.apiUrl}/api/auth/logout`);
    expect(req.request.method).toBe('POST');
    req.flush({ conversa_id: 'c1' });

    expect(feito).toBeTrue();
    expect(service.autenticado).toBeFalse();
    expect(service.token).toBeNull();
  });

  it('logout sem token não chama a API e limpa a sessão', () => {
    let chamadas = 0;
    service.logout().subscribe(() => chamadas++);

    http.expectNone(`${environment.apiUrl}/api/auth/logout`);
    expect(chamadas).toBe(1);
    expect(service.autenticado).toBeFalse();
  });

  it('deve restaurar a sessão do storage ao recriar o serviço', () => {
    service.login('a', 'b').subscribe();
    http.expectOne(urlLogin).flush({
      access_token: 't2',
      token_type: 'bearer',
      expires_in: 60,
      role: 'ALUNO',
      conversa_id: 'c2',
    } satisfies LoginResponse);

    const outro = TestBed.inject(AuthService);
    expect(outro.token).toBe('t2');
    expect(outro.role).toBe(Role.ALUNO);
  });
});
