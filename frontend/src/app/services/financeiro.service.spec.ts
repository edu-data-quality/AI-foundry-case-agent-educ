import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { FinanceiroService } from './financeiro.service';
import { Boleto } from '../models/boleto';

describe('FinanceiroService', () => {
  let service: FinanceiroService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(FinanceiroService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('consulta GET /api/financeiro/boleto com o cpf do aluno', () => {
    const cpf = '11144477735';
    service.obterBoletos(cpf).subscribe((boletos) => {
      expect(boletos.length).toBe(1);
      expect(boletos[0].linha_digitavel).toContain('23793');
    });

    const req = http.expectOne((r) => r.url === '/api/financeiro/boleto');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('cpf')).toBe(cpf);

    req.flush([
      {
        linha_digitavel: '23793.38128 60007.827130 95000.063308 6 88490000026000',
        qr_code_pix: '00020126580014br.gov.bcb.pix0136a1b2c3...',
        data_vencimento: '2026-12-10',
        status_pagamento: 'PENDENTE',
      },
    ] satisfies Boleto[]);
  });
});
