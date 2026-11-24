import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../core/auth/auth.service';
import { Role } from '../core/auth/role';

/**
 * Tela de login (issue #13, S3): autentica via `POST /api/auth/login` e
 * encaminha o usuário para a área da própria role (ALUNO → /aluno, ADMIN →
 * /admin). Já autenticado, desvia direto para a área correspondente.
 */
@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  formulario = this.fb.nonNullable.group({
    login: ['', Validators.required],
    senha: ['', Validators.required],
  });

  /** Mensagem de erro exibida ao usuário (credenciais inválidas, etc). */
  erro = '';
  enviando = false;

  ngOnInit(): void {
    if (this.auth.autenticado) {
      this.irParaAreaDaRole(this.auth.role ?? Role.ALUNO);
    }
  }

  entrar(): void {
    if (this.formulario.invalid || this.enviando) {
      return;
    }
    this.enviando = true;
    this.erro = '';
    const { login, senha } = this.formulario.getRawValue();
    this.auth.login(login, senha).subscribe({
      next: (resposta) => this.irParaAreaDaRole(resposta.role),
      error: (erro: HttpErrorResponse) => {
        this.enviando = false;
        this.erro =
          erro.status === 401
            ? 'Login ou senha inválidos.'
            : 'Falha ao entrar. Tente novamente.';
      },
    });
  }

  private irParaAreaDaRole(role: Role): void {
    const area = role === Role.ADMIN ? '/admin' : '/aluno';
    void this.router.navigateByUrl(area);
  }
}
