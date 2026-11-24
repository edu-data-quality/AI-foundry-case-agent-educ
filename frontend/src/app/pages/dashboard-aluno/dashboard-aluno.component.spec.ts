import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { DashboardAlunoComponent } from './dashboard-aluno.component';
import { authMockInterceptor } from '../../interceptors/auth-mock.interceptor';
import { MockSessaoAlunoService } from '../../services/mock-sessao-aluno.service';
import { SessaoAlunoService } from '../../services/sessao-aluno.service';
import { Boleto } from '../../models/boleto';
import { StatusAcademicoResposta } from '../../models/status-academico';

const CPF = '11144477735';

const STATUS_RESPONSA: StatusAcademicoResposta = {
  aluno: {
    id: 'uuid-1',
    cpf: CPF,
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
    {
      disciplina_id: 'uuid-d2',
      codigo: 'PROG102',
      nome: 'Programação Orientada a Objetos',
      semestre_letivo: '2026.1',
      nota_av1: 9.0,
      nota_av2: 8.0,
      nota_final: 8.5,
      status_disciplina: 'APROVADO',
    },
  ],
};

const BOLETOS_RESPONSA: Boleto[] = [
  {
    linha_digitavel: '23793.38128 60007.827130 95000.063308 6 88490000026000',
    qr_code_pix: '00020126580014br.gov.bcb.pix0136a1b2c3d4e5f6...',
    data_vencimento: '2026-12-10',
    status_pagamento: 'PENDENTE',
  },
  {
    linha_digitavel: null,
    qr_code_pix: null,
    data_vencimento: '2026-11-10',
    status_pagamento: 'ATRASADO',
  },
];

describe('DashboardAlunoComponent', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [DashboardAlunoComponent],
      providers: [
        provideHttpClient(withInterceptors([authMockInterceptor])),
        provideHttpClientTesting(),
        { provide: SessaoAlunoService, useClass: MockSessaoAlunoService },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function criarComponente() {
    const fixture = TestBed.createComponent(DashboardAlunoComponent);
    fixture.detectChanges();
    return fixture;
  }

  function servirRespostas() {
    http
      .expectOne((r) => r.url === '/api/aluno/status' && r.params.get('cpf') === CPF)
      .flush(STATUS_RESPONSA);
    http
      .expectOne((r) => r.url === '/api/financeiro/boleto' && r.params.get('cpf') === CPF)
      .flush(BOLETOS_RESPONSA);
  }

  it('exibe o nome e o curso do aluno', () => {
    const fixture = criarComponente();
    servirRespostas();
    fixture.detectChanges();

    const texto = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(texto).toContain('Maria Silva');
    expect(texto).toContain('Análise e Desenvolvimento de Sistemas');
  });

  it('lista disciplinas com notas av1, av2, final e situação', () => {
    const fixture = criarComponente();
    servirRespostas();
    fixture.detectChanges();

    const texto = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(texto).toContain('MAT101');
    expect(texto).toContain('Matemática Aplicada');
    expect(texto).toContain('8.5');
    expect(texto).toContain('7');
    expect(texto).toContain('Em andamento');
    expect(texto).toContain('PROG102');
    expect(texto).toContain('Aprovado');
  });

  it('exibe boletos com linha digitável, vencimento e QR Pix', () => {
    const fixture = criarComponente();
    servirRespostas();
    fixture.detectChanges();

    const texto = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(texto).toContain('23793.38128 60007.827130 95000.063308 6 88490000026000');
    expect(texto).toContain('10/12/2026');
    expect(texto).toContain('00020126580014br.gov.bcb.pix0136a1b2c3d4e5f6...');
    expect(texto).toContain('Pendente');
    expect(texto).toContain('Atrasado');
  });

  it('baixar boleto abre a impressão do boleto selecionado', () => {
    const fixture = criarComponente();
    servirRespostas();
    fixture.detectChanges();

    const printSpy = spyOn(window, 'print');
    const botoes = fixture.nativeElement.querySelectorAll('[data-testid="baixar-boleto"]');
    (botoes[0] as HTMLButtonElement).click();

    expect(fixture.componentInstance.boletoParaImprimir).toBe(BOLETOS_RESPONSA[0]);
    expect(printSpy).toHaveBeenCalled();
  });

  it('baixar boleto renderiza o detalhe imprimível do boleto selecionado', () => {
    const fixture = criarComponente();
    servirRespostas();
    fixture.detectChanges();

    const botoes = fixture.nativeElement.querySelectorAll('[data-testid="baixar-boleto"]');
    (botoes[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    const detalhe = fixture.nativeElement.querySelector('[data-testid="detalhe-boleto"]');
    expect(detalhe).not.toBeNull();
    const texto = detalhe?.textContent ?? '';
    expect(texto).toContain('23793.38128 60007.827130 95000.063308 6 88490000026000');
    expect(texto).toContain('00020126580014br.gov.bcb.pix0136a1b2c3d4e5f6...');
    expect(texto).toContain('10/12/2026');
    expect(texto).toContain('Pendente');
  });

  it('pedir declaração exibe aviso informativo (ação real no chat S14)', () => {
    const fixture = criarComponente();
    servirRespostas();
    fixture.detectChanges();

    const botoes = fixture.nativeElement.querySelectorAll('[data-testid="pedir-declaracao"]');
    (botoes[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    const texto = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(texto).toContain('em breve pelo chat');
  });
});
