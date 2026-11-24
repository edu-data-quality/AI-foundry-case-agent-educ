import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpCtrl: HttpTestingController;
  let auth: AuthService;
  const url = `${environment.apiUrl}/api/aluno/status`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        AuthService,
      ],
    });
    http = TestBed.inject(HttpClient);
    httpCtrl = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    localStorage.clear();
  });

  afterEach(() => {
    httpCtrl.verify();
    localStorage.clear();
  });

  it('injeta Authorization: Bearer quando há token', () => {
    localStorage.setItem(
      'ead.sessao',
      JSON.stringify({ access_token: 'jwt-abc', role: 'ALUNO', conversa_id: null }),
    );

    http.get(url).subscribe();

    const req = httpCtrl.expectOne(url);
    expect(req.request.headers.get('Authorization')).toBe('Bearer jwt-abc');
  });

  it('não injeta Authorization sem token', () => {
    http.get(url).subscribe();

    const req = httpCtrl.expectOne(url);
    expect(req.request.headers.has('Authorization')).toBeFalse();
  });

  it('limpa a sessão (token expirado) quando a API responde 401', () => {
    localStorage.setItem(
      'ead.sessao',
      JSON.stringify({ access_token: 'jwt-velho', role: 'ADMIN', conversa_id: null }),
    );

    http.get(url).subscribe({ error: () => undefined });

    httpCtrl.expectOne(url).flush(
      { detail: 'token expirado' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(auth.token).toBeNull();
    expect(localStorage.getItem('ead.sessao')).toBeNull();
  });
});
