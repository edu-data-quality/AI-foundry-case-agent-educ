import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AlunoDetalhe,
  AlunoResumo,
  CadastroAlunoPayload,
  MatriculaAtualizada,
  MensalidadeAtualizada,
  NotasMatriculaPayload,
  StatusPagamento,
} from '../models/admin-aluno';
import { StatusMatricula } from '../models/status-academico';

/**
 * Consome os endpoints admin de alunos (issues #16, #17 e #18):
 * `GET /api/admin/alunos?busca=` (listagem/busca),
 * `GET /api/admin/alunos/{id}` (detalhe),
 * `POST /api/admin/alunos` (cadastro para testes E2E) e os PATCHs do
 * simulador — notas, status de boleto e status de matrícula.
 *
 * O backend exige JWT de ADMIN; o header entra pelo `authInterceptor`.
 */
@Injectable({ providedIn: 'root' })
export class AdminAlunosService {
  private readonly http = inject(HttpClient);
  private readonly urlBase = `${environment.apiUrl}/api/admin/alunos`;

  /** Lista alunos; `busca` filtra por nome (trecho) ou CPF (prefixo). */
  listar(busca?: string): Observable<AlunoResumo[]> {
    let params = new HttpParams();
    const termo = busca?.trim();
    if (termo) {
      params = params.set('busca', termo);
    }
    return this.http.get<AlunoResumo[]>(this.urlBase, { params });
  }

  /** Detalhe do aluno com disciplinas e mensalidades. */
  detalhar(alunoId: string): Observable<AlunoDetalhe> {
    return this.http.get<AlunoDetalhe>(`${this.urlBase}/${alunoId}`);
  }

  /** Cadastra um novo aluno com dados fictícios para testes E2E. */
  criar(payload: CadastroAlunoPayload): Observable<AlunoResumo> {
    return this.http.post<AlunoResumo>(this.urlBase, payload);
  }

  /** Lança AV1/AV2/final e a situação da disciplina (simulador US4.2). */
  lancarNotas(
    alunoId: string,
    matriculaId: string,
    payload: NotasMatriculaPayload,
  ): Observable<MatriculaAtualizada> {
    return this.http.patch<MatriculaAtualizada>(
      `${this.urlBase}/${alunoId}/matriculas/${matriculaId}/notas`,
      payload,
    );
  }

  /** Altera o status do boleto (PENDENTE/PAGO/ATRASADO) em runtime. */
  alterarStatusMensalidade(
    mensalidadeId: string,
    status: StatusPagamento,
  ): Observable<MensalidadeAtualizada> {
    return this.http.patch<MensalidadeAtualizada>(
      `${environment.apiUrl}/api/admin/mensalidades/${mensalidadeId}/status`,
      { status },
    );
  }

  /** Altera o status de matrícula do aluno (ATIVO/TRANCADO/CONCLUIDO/INADIMPLENTE). */
  alterarStatusMatricula(
    alunoId: string,
    status: StatusMatricula,
  ): Observable<AlunoResumo> {
    return this.http.patch<AlunoResumo>(
      `${this.urlBase}/${alunoId}/matricula-status`,
      { status },
    );
  }
}
