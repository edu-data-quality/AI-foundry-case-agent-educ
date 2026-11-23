/**
 * Modelos do contrato `GET /api/aluno/status?cpf=` (issue #4).
 * Espelha os schemas Pydantic de backend/app/api/routes/aluno.py.
 */

export type StatusMatricula = 'ATIVO' | 'TRANCADO' | 'CONCLUIDO' | 'INADIMPLENTE';

export type StatusDisciplina =
  | 'EM_ANDAMENTO'
  | 'APROVADO'
  | 'REPROVADO'
  | 'AGUARDANDO_NOTA';

export interface DadosAluno {
  id: string;
  cpf: string;
  nome_completo: string;
  email: string;
  curso: string | null;
  polo: string | null;
  status_matricula: StatusMatricula;
}

export interface DisciplinaStatus {
  disciplina_id: string;
  codigo: string;
  nome: string;
  semestre_letivo: string;
  nota_av1: number | null;
  nota_av2: number | null;
  nota_final: number | null;
  status_disciplina: StatusDisciplina;
}

/** Resposta de `GET /api/aluno/status?cpf=` (schema StatusAcademicoResposta). */
export interface StatusAcademicoResposta {
  aluno: DadosAluno;
  disciplinas: DisciplinaStatus[];
}
