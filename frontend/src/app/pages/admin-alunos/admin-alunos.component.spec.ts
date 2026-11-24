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

  /** Abre o formulário e preenche dados válidos para o POST. */
  function preencherFormularioValido(componente: AdminAlunosComponent) {
    componente.abrirFormulario();
    componente.formulario.setValue({
      nome_completo: 'Novo Aluno Fictício',
      cpf: '529.982.247-25',
      email: 'novo@exemplo.com',
      telefone: '(11) 99999-0000',
      curso: 'ADS',
      polo: 'Recife',
      status_matricula: 'TRANCADO',
    });
  }

  const NOVO_ALUNO: AlunoResumo = {
    id: 'uuid-aluno-novo',
    cpf: '52998224725',
    nome_completo: 'Novo Aluno Fictício',
    email: 'novo@exemplo.com',
    telefone: '(11) 99999-0000',
    curso: 'ADS',
    polo: 'Recife',
    status_matricula: 'TRANCADO',
  };

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
      'table.tabela-alunos button.acao',
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
      'table.tabela-alunos button.acao',
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

  it('abre o formulário de cadastro com os campos do PRD', () => {
    const fixture = criarComponente();

    const botaoNovo = fixture.nativeElement.querySelector(
      'button.novo-aluno',
    ) as HTMLButtonElement;
    botaoNovo.click();
    fixture.detectChanges();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Novo aluno');
    expect(
      fixture.nativeElement.querySelector('form input#nome_completo'),
    ).not.toBeNull();
    expect(fixture.nativeElement.querySelector('form input#cpf')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('form input#email')).not.toBeNull();
    expect(
      fixture.nativeElement.querySelector('form input#telefone'),
    ).not.toBeNull();
    expect(fixture.nativeElement.querySelector('form input#curso')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('form input#polo')).not.toBeNull();
    expect(
      fixture.nativeElement.querySelector('form select#status_matricula'),
    ).not.toBeNull();
  });

  it('envia o cadastro válido e exibe atalho para o aluno criado', () => {
    const fixture = criarComponente();
    const componente = fixture.componentInstance;
    preencherFormularioValido(componente);

    componente.cadastrar();

    const req = http.expectOne((r) => r.url === URL_BASE && r.method === 'POST');
    expect(req.request.body).toEqual({
      nome_completo: 'Novo Aluno Fictício',
      cpf: '52998224725',
      email: 'novo@exemplo.com',
      telefone: '(11) 99999-0000',
      curso: 'ADS',
      polo: 'Recife',
      status_matricula: 'TRANCADO',
    });
    req.flush(NOVO_ALUNO);
    fixture.detectChanges();

    // Cadastro recarrega a listagem sem filtro para o aluno aparecer.
    const listagem = http.expectOne((r) => r.url === URL_BASE && r.method === 'GET');
    expect(listagem.request.params.has('busca')).toBeFalse();
    listagem.flush([...ALUNOS, NOVO_ALUNO]);
    fixture.detectChanges();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Novo Aluno Fictício cadastrado com sucesso.');
    expect(texto).toContain('Ir para o aluno');
    expect(fixture.nativeElement.querySelector('.form-cadastro')).toBeNull();
    expect(
      (fixture.nativeElement.querySelector('.sucesso button') as HTMLButtonElement)
        .textContent,
    ).toContain('Ir para o aluno');

    const atalho = fixture.nativeElement.querySelector(
      '.sucesso button',
    ) as HTMLButtonElement;
    atalho.click();
    http.expectOne(`${URL_BASE}/${NOVO_ALUNO.id}`).flush({
      aluno: NOVO_ALUNO,
      disciplinas: [],
      mensalidades: [],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Aluno sem disciplinas matriculadas.');
  });

  it('mostra mensagem amigável para CPF duplicado (409)', () => {
    const fixture = criarComponente();
    const componente = fixture.componentInstance;
    preencherFormularioValido(componente);

    componente.cadastrar();
    http
      .expectOne((r) => r.url === URL_BASE && r.method === 'POST')
      .flush({ detail: 'CPF já cadastrado' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('CPF já cadastrado');
  });

  it('mostra mensagem de acesso negado quando a API responde 403', () => {
    const fixture = criarComponente();
    const componente = fixture.componentInstance;
    preencherFormularioValido(componente);

    componente.cadastrar();
    http
      .expectOne((r) => r.url === URL_BASE && r.method === 'POST')
      .flush({ detail: 'proibido' }, { status: 403, statusText: 'Forbidden' });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Apenas administradores podem cadastrar alunos',
    );
  });

  it('bloqueia CPF inválido antes de chamar a API', () => {
    const fixture = criarComponente();
    const componente = fixture.componentInstance;
    preencherFormularioValido(componente);
    componente.formulario.controls.cpf.setValue('111.111.111-11');

    componente.cadastrar();
    fixture.detectChanges();

    http.expectNone((r) => r.url === URL_BASE && r.method === 'POST');
    expect(fixture.nativeElement.textContent).toContain('CPF inválido.');
  });
});
