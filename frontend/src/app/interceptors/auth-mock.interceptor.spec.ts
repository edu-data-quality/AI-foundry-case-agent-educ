import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { authMockInterceptor } from './auth-mock.interceptor';
import { MockSessaoAlunoService } from '../services/mock-sessao-aluno.service';
import { SessaoAlunoService } from '../services/sessao-aluno.service';

describe('authMockInterceptor', () => {
  let http: HttpTestingController;
  let httpClient: HttpClient;
  let sessao: SessaoAlunoService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authMockInterceptor])),
        provideHttpClientTesting(),
        { provide: SessaoAlunoService, useClass: MockSessaoAlunoService },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    httpClient = TestBed.inject(HttpClient);
    sessao = TestBed.inject(SessaoAlunoService);
  });

  afterEach(() => http.verify());

  it('injeta Authorization Bearer com o token da sessão', () => {
    httpClient
      .get('/api/aluno/status', { params: { cpf: '11144477735' } })
      .subscribe();

    const req = http.expectOne((r) => r.url === '/api/aluno/status');
    expect(req.request.headers.get('Authorization')).toBe(`Bearer ${sessao.token}`);
    req.flush({ ok: true });
  });
});
