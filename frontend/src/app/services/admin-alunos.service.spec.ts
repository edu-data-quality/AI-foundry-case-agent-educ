import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../environments/environment';
import { AlunoDetalhe, AlunoResumo } from '../models/admin-aluno';
import { AdminAlunosService } from './admin-alunos.service';

const URL_BASE = `${environment.apiUrl}/api/admin/alunos`;

const ALUNO: AlunoResumo = {
  id: 'uuid-aluno-1',
  cpf: '11122233344',
  nome_completo: 'Aluna Teste',
  email: 'aluna@exemplo.com',
  telefone: '11999990000',
  curso: 'ADS',
  polo: 'São Paulo',
  status_matricula: 'ATIVO',
};

const DETALHE: AlunoDetalhe = {
  aluno: ALUNO,
  disciplinas: [
    {
      disciplina_id: 'uuid-d1',
      codigo: 'ADS101',
      nome: 'Algoritmos',
      semestre_letivo: '2026.1',
      nota_av1: 8.5,
      nota_av2: null,
      nota_final: null,
      status_disciplina: 'EM_ANDAMENTO',
    },
  ],
  mensalidades: [
    {
      id: 'uuid-m1',
      aluno_id: ALUNO.id,
      mes_referencia: '2026-11',
      valor_original: 450,
      data_vencimento: '2026-11-10',
      status_pagamento: 'PENDENTE',
    },
  ],
};

describe('AdminAlunosService', () => {
  let service: AdminAlunosService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AdminAlunosService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lista alunos sem filtro', () => {
    let recebidos: AlunoResumo[] = [];
    service.listar().subscribe((alunos) => (recebidos = alunos));

    const req = http.expectOne((r) => r.url === URL_BASE && r.method === 'GET');
    expect(req.request.params.has('busca')).toBeFalse();
    req.flush([ALUNO]);

    expect(recebidos).toEqual([ALUNO]);
  });

  it('envia a busca por nome/CPF como query param', () => {
    service.listar('  111  ').subscribe();

    const req = http.expectOne((r) => r.url === URL_BASE && r.method === 'GET');
    expect(req.request.params.get('busca')).toBe('111');
    req.flush([]);
  });

  it('não envia o parâmetro busca quando o termo é vazio', () => {
    service.listar('   ').subscribe();

    const req = http.expectOne((r) => r.url === URL_BASE && r.method === 'GET');
    expect(req.request.params.has('busca')).toBeFalse();
    req.flush([]);
  });

  it('consulta o detalhe do aluno por id', () => {
    let recebido: AlunoDetalhe | null = null;
    service.detalhar(ALUNO.id).subscribe((detalhe) => (recebido = detalhe));

    const req = http.expectOne((r) => r.url === `${URL_BASE}/${ALUNO.id}`);
    expect(req.request.method).toBe('GET');
    req.flush(DETALHE);

    expect(recebido!).toEqual(DETALHE);
  });
});
