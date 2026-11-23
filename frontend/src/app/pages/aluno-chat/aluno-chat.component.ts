import { Component } from '@angular/core';

/**
 * Área do aluno — /aluno (issue #13). A tela do chat (US3.1) entra em issue
 * futura; aqui o roteamento por role já entrega a área correta após o login.
 */
@Component({
  selector: 'app-aluno-chat',
  imports: [],
  template: `
    <section class="pagina">
      <h1>Chat do Aluno</h1>
      <p class="aviso">
        Área do aluno. O chat integrado com o agente (Azure AI Foundry) será
        construído na próxima história (US3.1).
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
export class AlunoChatComponent {}
