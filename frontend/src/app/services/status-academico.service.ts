import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { StatusAcademicoResposta } from '../models/status-academico';

/**
 * Consome `GET /api/aluno/status?cpf=` (issue #4).
 * O CPF vem de quem chama (no dashboard, do aluno logado via SessaoAlunoService).
 */
@Injectable({ providedIn: 'root' })
export class StatusAcademicoService {
  private readonly url = '/api/aluno/status';

  constructor(private readonly http: HttpClient) {}

  obterStatus(cpf: string): Observable<StatusAcademicoResposta> {
    return this.http.get<StatusAcademicoResposta>(this.url, { params: { cpf } });
  }
}
