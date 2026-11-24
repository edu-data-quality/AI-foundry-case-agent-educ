import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { AlunoDetalhe, AlunoResumo } from '../../models/admin-aluno';
import { AdminAlunosComponent } from './admin-alunos.component';

const URL_BASE = `${environment.apiUrl}/api/admin/alunos`;

const ALUNOS: AlunoResumo[] = [
  {
    id: 'uuid-aluno-1',
    cpf: '11122233344',
    nome_completo: 'Aluna Teste',
    email: 'aluna@exemplo.com',
    telefone: null,
    curso: 'ADS',
    polo: 'São Paulo',
    status_matricula: 'ATIVO',
  },
  {
    id: 'uuid-aluno-2',
    cpf: '99988877766',
    nome_completo: 'Bruno Souza',
    email: 'bruno@exemplo.com',
    telefone: null,
    curso: null,
    polo: null,
    status_matricula: 'TRANCADO',
  },
];

const DETALHE: AlunoDetalhe = {
  aluno: ALUNOS[0],
  disciplinas: [
    {
      disciplina_id: 'uuid-d1',
      codigo: 'ADS101',
      nome: 'Algoritmos',
      semestre_letivo: '2026.1',
      nota_av1: 8.5,
      nota_av2: 7,
      nota_final: null,
      status_disciplina: 'EM_ANDAMENTO',
    },
  ],
  mensalidades: [
    {
      id: 'uuid-m1',
      aluno_id: ALUNOS[0].id,
      mes_referencia: '2026-11',
      valor_original: 450,
      data_vencimento: '2026-11-10',
      status_pagamento: 'PENDENTE',
    },
  ],
};

describe('AdminAlunosComponent', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AdminAlunosComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  /** Cria o componente e responde à listagem inicial do `ngOnInit`. */
  function criarComponente(alunos: AlunoResumo[] = ALUNOS) {
    const fixture = TestBed.createComponent(AdminAlunosComponent);
    fixture.detectChanges();
    http
      .expectOne((r) => r.url === URL_BASE && r.method === 'GET')
      .flush(alunos);
    fixture.detectChanges();
    return fixture;
  }

  it('carrega e exibe a listagem de alunos no init', () => {
    const fixture = criarComponente();
    const texto = fixture.nativeElement.textContent as string;

    expect(texto).toContain('Aluna Teste');
    expect(texto).toContain('11122233344');
    expect(texto).toContain('ADS');
    expect(texto).toContain('São Paulo');
    expect(texto).toContain('Ativo');
    expect(texto).toContain('Bruno Souza');
    expect(texto).toContain('Trancado');
  });

  it('busca por nome/CPF enviando o termo para a API', () => {
    const fixture = criarComponente();
    const componente = fixture.componentInstance;

    componente.busca = 'Bruno';
    const botao = fixture.nativeElement.querySelector(
      'form.busca button[type="submit"]',
    ) as HTMLButtonElement;
    botao.click();

    const req = http.expectOne(
      (r) => r.url === URL_BASE && r.params.get('busca') === 'Bruno',
    );
    req.flush([ALUNOS[1]]);
    fixture.detectChanges();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Bruno Souza');
    expect(texto).not.toContain('Aluna Teste');
  });

  it('abre o detalhe com disciplinas e mensalidades ao clicar em Detalhes', () => {
    const fixture = criarComponente();

    const botoes = fixture.nativeElement.querySelectorAll(
      'button.acao',
    ) as NodeListOf<HTMLButtonElement>;
    botoes[0].click();

    const req = http.expectOne(`${URL_BASE}/${ALUNOS[0].id}`);
    expect(req.request.method).toBe('GET');
    req.flush(DETALHE);
    fixture.detectChanges();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Disciplinas');
    expect(texto).toContain('ADS101');
    expect(texto).toContain('Algoritmos');
    expect(texto).toContain('Em andamento');
    expect(texto).toContain('Mensalidades');
    expect(texto).toContain('11/2026');
    expect(texto).toContain('10/11/2026');
    expect(texto).toContain('Pendente');
  });

  it('fecha o detalhe ao clicar em Fechar', () => {
    const fixture = criarComponente();

    const botaoDetalhes = fixture.nativeElement.querySelector(
      'button.acao',
    ) as HTMLButtonElement;
    botaoDetalhes.click();
    http.expectOne(`${URL_BASE}/${ALUNOS[0].id}`).flush(DETALHE);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.detalhe')).not.toBeNull();

    const botaoFechar = fixture.nativeElement.querySelector(
      '.detalhe .acao',
    ) as HTMLButtonElement;
    botaoFechar.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.detalhe')).toBeNull();
  });

  it('mostra mensagem de lista vazia', () => {
    const fixture = criarComponente([]);

    expect(fixture.nativeElement.textContent).toContain('Nenhum aluno encontrado.');
  });

  it('mostra erro quando a listagem falha', () => {
    const fixture = TestBed.createComponent(AdminAlunosComponent);
    fixture.detectChanges();
    http
      .expectOne((r) => r.url === URL_BASE && r.method === 'GET')
      .flush(null, { status: 500, statusText: 'Erro' });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Não foi possível carregar os alunos',
    );
  });
});
