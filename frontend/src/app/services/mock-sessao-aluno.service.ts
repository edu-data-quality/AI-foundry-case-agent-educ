import { Injectable } from '@angular/core';

import { SessaoAlunoService } from './sessao-aluno.service';

/**
 * MOCK provisório da sessão do aluno (issue #15).
 *
 * O CPF e o token são fictícios para a página funcionar isolada enquanto o
 * guard/interceptor do #13 (app shell) não existe na base. Quando o #13 for
 * merged, trocar o provider deste mock pela sessão real (token JWT do login).
 */
@Injectable()
export class MockSessaoAlunoService extends SessaoAlunoService {
  override cpf = '11144477735'; // CPF do seed de demonstração do backend
  override token = 'token-mock-dashboard-15';
}
