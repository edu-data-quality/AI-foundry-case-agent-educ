/**
 * Contrato de sessão do aluno logado (issue #15).
 *
 * VIRTUAL: o guard/interceptor reais do #13 (app shell) ainda não existem na
 * base desta branch. Esta abstração é o ponto único em que o dashboard obtém
 * CPF e token; hoje é satisfeita por `MockSessaoAlunoService`.
 */
export abstract class SessaoAlunoService {
  abstract cpf: string | null;
  abstract token: string | null;
}
