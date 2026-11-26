/**
 * Modelos dos contratos admin de alunos (issue #16).
 * Espelha os schemas Pydantic de backend/app/api/routes/admin.py.
 */

import { StatusMatricula } from './status-academico';

export type StatusPagamento = 'PENDENTE' | 'PAGO' | 'ATRASADO';

export type StatusDisciplina =
  | 'EM_ANDAMENTO'
  | 'APROVADO'
  | 'REPROVADO'
  | 'AGUARDANDO_NOTA';

/** Payload de `POST /api/admin/alunos` (schema CadastroAluno). */
export interface CadastroAlunoPayload {
  cpf: string;
  nome_completo: string;
  email: string;
  telefone?: string | null;
  curso?: string | null;
  polo?: string | null;
  status_matricula: StatusMatricula;
}

/** Item de `GET /api/admin/alunos` (schema AlunoResposta). */
export interface AlunoResumo {
  id: string;
  cpf: string;
  nome_completo: string;
  email: string;
  telefone: string | null;
  curso: string | null;
  polo: string | null;
  status_matricula: StatusMatricula;
}

/** Disciplina do aluno no detalhe admin (schema DisciplinaAlunoResposta). */
export interface DisciplinaAluno {
  /** Id da matrícula, usado no PATCH de notas do simulador. */
  matricula_id: string;
  disciplina_id: string;
  codigo: string;
  nome: string;
  semestre_letivo: string;
  nota_av1: number | null;
  nota_av2: number | null;
  nota_final: number | null;
  status_disciplina: StatusDisciplina;
}

/** Mensalidade do aluno no detalhe admin (schema MensalidadeAlunoResposta). */
export interface MensalidadeAluno {
  id: string;
  aluno_id: string;
  mes_referencia: string;
  valor_original: number;
  data_vencimento: string;
  status_pagamento: StatusPagamento;
}

/** Resposta de `GET /api/admin/alunos/{aluno_id}` (schema AlunoDetalheResposta). */
export interface AlunoDetalhe {
  aluno: AlunoResumo;
  disciplinas: DisciplinaAluno[];
  mensalidades: MensalidadeAluno[];
}

/** Payload de `PATCH .../matriculas/{matricula_id}/notas` (schema NotasMatricula). */
export interface NotasMatriculaPayload {
  nota_av1: number | null;
  nota_av2: number | null;
  nota_final: number | null;
  status_disciplina: StatusDisciplina;
}

/** Resposta do PATCH de notas (schema MatriculaResposta). */
export interface MatriculaAtualizada {
  id: string;
  disciplina_id: string;
  semestre_letivo: string;
  nota_av1: number | null;
  nota_av2: number | null;
  nota_final: number | null;
  status_disciplina: StatusDisciplina;
}

/** Resposta de `PATCH /api/admin/mensalidades/{id}/status` (schema MensalidadeResposta). */
export interface MensalidadeAtualizada {
  id: string;
  aluno_id: string;
  mes_referencia: string;
  status_pagamento: StatusPagamento;
}
