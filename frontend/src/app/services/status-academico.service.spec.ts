import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { StatusAcademicoService } from './status-academico.service';
import { StatusAcademicoResposta } from '../models/status-academico';

describe('StatusAcademicoService', () => {
  let service: StatusAcademicoService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(StatusAcademicoService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('consulta GET /api/aluno/status com o cpf do aluno', () => {
    const cpf = '11144477735';
    service.obterStatus(cpf).subscribe((resposta) => {
      expect(resposta.aluno.nome_completo).toBe('Maria Silva');
    });

    const req = http.expectOne((r) => r.url === '/api/aluno/status');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('cpf')).toBe(cpf);

    req.flush({
      aluno: {
        id: 'uuid-1',
        cpf,
        nome_completo: 'Maria Silva',
        email: 'maria@email.com',
        curso: 'Análise e Desenvolvimento de Sistemas',
        polo: 'São Paulo',
        status_matricula: 'ATIVO',
      },
      disciplinas: [
        {
          disciplina_id: 'uuid-d1',
          codigo: 'MAT101',
          nome: 'Matemática Aplicada',
          semestre_letivo: '2026.1',
          nota_av1: 8.5,
          nota_av2: 7.0,
          nota_final: null,
          status_disciplina: 'EM_ANDAMENTO',
        },
      ],
    } satisfies StatusAcademicoResposta);
  });
});
