import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { LoginRequest, LoginResponse } from './auth.model';
import { Role } from './role';

/** Formato da sessão persistida no `localStorage`. */
export interface SessaoPersistida {
  access_token: string;
  role: Role;
  conversa_id: string | null;
}

const CHAVE_SESSAO = 'ead.sessao';

/**
 * Autenticação do portal (issue #13).
 *
 * Consome `POST /api/auth/login` e `POST /api/auth/logout`, persiste a sessão
 * (token, role, conversa_id) no `localStorage` e a restaura a cada acesso —
 * sobrevive a reload e a múltiplas instâncias do serviço (DI singleton).
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  /** Token JWT atual, ou `null` se não autenticado. */
  get token(): string | null {
    return this.sessao()?.access_token ?? null;
  }

  /** Role do usuário autenticado (ALUNO | ADMIN), ou `null`. */
  get role(): Role | null {
    return this.sessao()?.role ?? null;
  }

  /** ID da sessão de chat retomada no login (apenas ALUNO). */
  get conversaId(): string | null {
    return this.sessao()?.conversa_id ?? null;
  }

  /** `true` quando há um token de acesso válido em sessão. */
  get autenticado(): boolean {
    return this.token !== null;
  }

  /**
   * Autentica login + senha. Persiste a sessão devolvida pelo backend e
   * expõe a resposta completa para o chamador navegar pela role.
   */
  login(login: string, senha: string): Observable<LoginResponse> {
    const payload: LoginRequest = { login, senha };
    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/api/auth/login`, payload)
      .pipe(
        map((resposta) => {
          this.persistir(resposta);
          return resposta;
        }),
      );
  }

  /**
   * Encerra a sessão no backend (`POST /api/auth/logout`) quando há token e
   * remove a sessão local. Nunca falha para o chamador: o logout local sempre
   * acontece.
   */
  logout(): Observable<void> {
    const token = this.token;
    if (token === null) {
      this.limpar();
      return new Observable<void>((observer) => {
        observer.next();
        observer.complete();
      });
    }
    return new Observable<void>((observer) => {
      this.http
        .post(`${environment.apiUrl}/api/auth/logout`, null)
        .subscribe({
          next: () => {
            this.limpar();
            observer.next();
            observer.complete();
          },
          error: () => {
            // Offline/idempotência: o backend permite logout sem sessão e o
            // token continua válido até expirar — o front descarta o token.
            this.limpar();
            observer.next();
            observer.complete();
          },
        });
    });
  }

  /** Remove a sessão local sem chamar o backend (ex: sessão expirada). */
  limpar(): void {
    localStorage.removeItem(CHAVE_SESSAO);
  }

  private sessao(): SessaoPersistida | null {
    const raw = localStorage.getItem(CHAVE_SESSAO);
    if (raw === null) {
      return null;
    }
    try {
      const sessao = JSON.parse(raw) as SessaoPersistida;
      if (typeof sessao.access_token !== 'string' || sessao.access_token === '') {
        return null;
      }
      return sessao;
    } catch {
      return null;
    }
  }

  private persistir(resposta: LoginResponse): void {
    const sessao: SessaoPersistida = {
      access_token: resposta.access_token,
      role: resposta.role,
      conversa_id: resposta.conversa_id,
    };
    localStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
  }
}
