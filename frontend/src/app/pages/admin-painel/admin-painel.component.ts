import { Component } from '@angular/core';

/**
 * Painel administrativo — /admin (issue #13). O CRUD/simulador (US4.x) entra
 * no Épico 4; aqui o roteamento por role já protege a área do ADMIN.
 */
@Component({
  selector: 'app-admin-painel',
  imports: [],
  template: `
    <section class="pagina">
      <h1>Painel do Administrador</h1>
      <p class="aviso">
        Área do admin. O painel com cadastro de alunos, lançamento de notas e
        simulação de boletos será construído no Épico 4 (US4.1).
      </p>
    </section>
  `,
  styles: `
    .pagina h1 {
      margin: 0 0 0.5rem;
      font-size: 1.25rem;
      color: #1f2937;
    }
    .pagina .aviso {
      color: #4b5563;
    }
  `,
})
export class AdminPainelComponent {}
