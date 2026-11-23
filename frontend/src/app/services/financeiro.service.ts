import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Boleto } from '../models/boleto';

/**
 * Consome `GET /api/financeiro/boleto?cpf=` (issue #5).
 * O CPF vem de quem chama (no dashboard, do aluno logado via SessaoAlunoService).
 */
@Injectable({ providedIn: 'root' })
export class FinanceiroService {
  private readonly url = '/api/financeiro/boleto';

  constructor(private readonly http: HttpClient) {}

  obterBoletos(cpf: string): Observable<Boleto[]> {
    return this.http.get<Boleto[]>(this.url, { params: { cpf } });
  }
}
