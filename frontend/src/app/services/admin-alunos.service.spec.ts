import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../environments/environment';
import {
  AlunoDetalhe,
  AlunoResumo,
  CadastroAlunoPayload,
} from '../models/admin-aluno';
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
      matricula_id: 'uuid-mat-1',
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

  it('cadastra aluno via POST /api/admin/alunos', () => {
    const payload: CadastroAlunoPayload = {
      nome_completo: 'Novo Aluno',
      cpf: '52998224725',
      email: 'novo@exemplo.com',
      telefone: null,
      curso: 'ADS',
      polo: 'Recife',
      status_matricula: 'ATIVO',
    };
    let recebido: AlunoResumo | null = null;
    service.criar(payload).subscribe((aluno) => (recebido = aluno));

    const req = http.expectOne((r) => r.url === URL_BASE && r.method === 'POST');
    expect(req.request.body).toEqual(payload);
    req.flush({ ...ALUNO, ...payload });

    expect(recebido!).toEqual({ ...ALUNO, ...payload });
  });

  it('lança notas via PATCH da matrícula (simulador #18)', () => {
    const payload = {
      nota_av1: 9.5,
      nota_av2: 8,
      nota_final: null,
      status_disciplina: 'APROVADO' as const,
    };
    let recebido: unknown = null;
    service
      .lancarNotas(ALUNO.id, 'uuid-mat-1', payload)
      .subscribe((matricula) => (recebido = matricula));

    const req = http.expectOne(
      `${URL_BASE}/${ALUNO.id}/matriculas/uuid-mat-1/notas`,
    );
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual(payload);
    req.flush({
      id: 'uuid-mat-1',
      disciplina_id: 'uuid-d1',
      semestre_letivo: '2026.1',
      ...payload,
    });

    expect(recebido).toEqual({
      id: 'uuid-mat-1',
      disciplina_id: 'uuid-d1',
      semestre_letivo: '2026.1',
      ...payload,
    });
  });

  it('altera status de mensalidade via PATCH', () => {
    let recebido: unknown = null;
    service
      .alterarStatusMensalidade('uuid-m1', 'PAGO')
      .subscribe((mensalidade) => (recebido = mensalidade));

    const req = http.expectOne(
      `${environment.apiUrl}/api/admin/mensalidades/uuid-m1/status`,
    );
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ status: 'PAGO' });
    req.flush({ ...DETALHE.mensalidades[0], status_pagamento: 'PAGO' });

    expect(recebido).toEqual({ ...DETALHE.mensalidades[0], status_pagamento: 'PAGO' });
  });

  it('altera status de matrícula via PATCH', () => {
    let recebido: AlunoResumo | null = null;
    service
      .alterarStatusMatricula(ALUNO.id, 'TRANCADO')
      .subscribe((aluno) => (recebido = aluno));

    const req = http.expectOne(`${URL_BASE}/${ALUNO.id}/matricula-status`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ status: 'TRANCADO' });
    req.flush({ ...ALUNO, status_matricula: 'TRANCADO' });

    expect(recebido!).toEqual({ ...ALUNO, status_matricula: 'TRANCADO' });
  });
});
