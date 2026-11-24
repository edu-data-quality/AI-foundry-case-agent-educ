import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { AlunoDetalhe, AlunoResumo } from '../models/admin-aluno';

/**
 * Consome os endpoints admin de alunos (issue #16):
 * `GET /api/admin/alunos?busca=` (listagem/busca) e
 * `GET /api/admin/alunos/{id}` (detalhe com disciplinas e mensalidades).
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
}
