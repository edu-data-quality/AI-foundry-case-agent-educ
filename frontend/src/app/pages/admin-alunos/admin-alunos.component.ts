import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';

import { cpfValidator } from '../../core/validators/cpf.validator';
import {
  AlunoDetalhe,
  AlunoResumo,
  CadastroAlunoPayload,
  DisciplinaAluno,
  MensalidadeAluno,
  NotasMatriculaPayload,
  StatusDisciplina,
  StatusPagamento,
} from '../../models/admin-aluno';
import { StatusMatricula } from '../../models/status-academico';
import { AdminAlunosService } from '../../services/admin-alunos.service';

const ROTULO_STATUS_MATRICULA: Record<StatusMatricula, string> = {
  ATIVO: 'Ativo',
  TRANCADO: 'Trancado',
  CONCLUIDO: 'Concluído',
  INADIMPLENTE: 'Inadimplente',
};

const ROTULO_STATUS_DISCIPLINA: Record<StatusDisciplina, string> = {
  EM_ANDAMENTO: 'Em andamento',
  APROVADO: 'Aprovado',
  REPROVADO: 'Reprovado',
  AGUARDANDO_NOTA: 'Aguardando nota',
};

const ROTULO_STATUS_PAGAMENTO: Record<StatusPagamento, string> = {
  PENDENTE: 'Pendente',
  PAGO: 'Pago',
  ATRASADO: 'Atrasado',
};

/** Rascunho editável das notas de uma matrícula (simulador US4.2). */
interface NotasRascunho {
  nota_av1: number | null;
  nota_av2: number | null;
  nota_final: number | null;
  status_disciplina: StatusDisciplina;
}

type CampoFormulario =
  | 'nome_completo'
  | 'cpf'
  | 'email'
  | 'telefone'
  | 'curso'
  | 'polo'
  | 'status_matricula';

/**
 * Área admin de alunos — /admin/alunos (issues #16, #17 e #18, US4.1/US4.2).
 *
 * Lista alunos, busca por nome/CPF na API Admin e abre o detalhe com
 * disciplinas e mensalidades. O formulário de cadastro (#17) envia dados
 * fictícios para `POST /api/admin/alunos`; o simulador (#18) lança notas,
 * altera status de boleto e de matrícula pelos PATCHs da API Admin e reflete
 * o resultado na hora (S4/S14), sem reiniciar o banco.
 */
@Component({
  selector: 'app-admin-alunos',
  imports: [FormsModule, ReactiveFormsModule, RouterLink],
  templateUrl: './admin-alunos.component.html',
  styleUrl: './admin-alunos.component.css',
})
export class AdminAlunosComponent implements OnInit {
  private readonly alunosService = inject(AdminAlunosService);
  private readonly fb = inject(FormBuilder);

  readonly statusMatriculaOpcoes: StatusMatricula[] = [
    'ATIVO',
    'TRANCADO',
    'CONCLUIDO',
    'INADIMPLENTE',
  ];

  readonly statusDisciplinaOpcoes: StatusDisciplina[] = [
    'EM_ANDAMENTO',
    'APROVADO',
    'REPROVADO',
    'AGUARDANDO_NOTA',
  ];

  readonly statusPagamentoOpcoes: StatusPagamento[] = [
    'PENDENTE',
    'PAGO',
    'ATRASADO',
  ];

  alunos: AlunoResumo[] = [];
  busca = '';
  carregando = false;
  erroListagem = false;

  detalhe: AlunoDetalhe | null = null;
  carregandoDetalhe = false;
  erroDetalhe = false;

  /** Estado do simulador em runtime (issue #18 / US4.2). */
  notasRascunho: Record<string, NotasRascunho> = {};
  statusPagamentoRascunho: Record<string, StatusPagamento> = {};
  statusMatriculaSelecionado: StatusMatricula = 'ATIVO';
  salvandoNotas: Record<string, boolean> = {};
  salvandoMensalidade: Record<string, boolean> = {};
  salvandoStatusMatricula = false;
  mensagemAtualizacao = '';
  erroAtualizacao = '';

  /** Estado do formulário de cadastro (US4.1). */
  formularioAberto = false;
  enviando = false;
  erroCadastro = '';
  mensagemSucesso = '';
  alunoCriado: AlunoResumo | null = null;

  formulario = this.fb.nonNullable.group({
    nome_completo: ['', [Validators.required, Validators.minLength(3)]],
    cpf: ['', [Validators.required, cpfValidator]],
    email: ['', [Validators.required, Validators.email]],
    telefone: ['', [Validators.pattern(/^[0-9()+\-\s]*$/)]],
    curso: ['', [Validators.required]],
    polo: ['', [Validators.required]],
    status_matricula: ['ATIVO' as StatusMatricula],
  });

  ngOnInit(): void {
    this.pesquisar();
  }

  /** Busca na API; termo vazio devolve a listagem completa. */
  pesquisar(): void {
    this.carregando = true;
    this.erroListagem = false;
    this.alunosService.listar(this.busca).subscribe({
      next: (alunos) => {
        this.alunos = alunos;
        this.carregando = false;
      },
      error: () => {
        this.erroListagem = true;
        this.carregando = false;
      },
    });
  }

  /** Abre o formulário de cadastro em branco. */
  abrirFormulario(): void {
    this.erroCadastro = '';
    this.mensagemSucesso = '';
    this.alunoCriado = null;
    this.formularioAberto = true;
  }

  /** Fecha o formulário e descarta o rascunho. */
  fecharFormulario(): void {
    this.formularioAberto = false;
    this.erroCadastro = '';
    this.limparFormulario();
  }

  /** Envia o cadastro para `POST /api/admin/alunos`. */
  cadastrar(): void {
    this.erroCadastro = '';
    this.mensagemSucesso = '';

    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    if (this.enviando) {
      return;
    }

    this.enviando = true;
    const dados = this.formulario.getRawValue();
    const payload: CadastroAlunoPayload = {
      nome_completo: dados.nome_completo.trim(),
      cpf: dados.cpf.replace(/\D/g, ''),
      email: dados.email.trim(),
      telefone: dados.telefone.trim() || null,
      curso: dados.curso.trim(),
      polo: dados.polo.trim(),
      status_matricula: dados.status_matricula,
    };

    this.alunosService.criar(payload).subscribe({
      next: (aluno) => {
        this.enviando = false;
        this.alunoCriado = aluno;
        this.mensagemSucesso = `Aluno ${aluno.nome_completo} cadastrado com sucesso.`;
        this.formularioAberto = false;
        this.limparFormulario();
        this.busca = '';
        this.pesquisar();
      },
      error: (erro: HttpErrorResponse) => {
        this.enviando = false;
        this.erroCadastro = this.mensagemErroCadastro(erro);
      },
    });
  }

  /** Abre o detalhe do aluno recém-cadastrado. */
  irParaAlunoCriado(): void {
    if (this.alunoCriado !== null) {
      this.abrirDetalhe(this.alunoCriado);
    }
  }

  /** `true` quando o campo deve exibir a mensagem de validação. */
  campoInvalido(campo: CampoFormulario): boolean {
    const controle = this.formulario.get(campo);
    return controle !== null && controle.invalid && (controle.touched || controle.dirty);
  }

  /** Abre o detalhe do aluno selecionado (disciplinas + mensalidades). */
  abrirDetalhe(aluno: AlunoResumo): void {
    this.carregandoDetalhe = true;
    this.erroDetalhe = false;
    this.detalhe = null;
    this.mensagemAtualizacao = '';
    this.erroAtualizacao = '';
    this.alunosService.detalhar(aluno.id).subscribe({
      next: (detalhe) => {
        this.detalhe = detalhe;
        this.inicializarSimulador(detalhe);
        this.carregandoDetalhe = false;
      },
      error: () => {
        this.erroDetalhe = true;
        this.carregandoDetalhe = false;
      },
    });
  }

  fecharDetalhe(): void {
    this.detalhe = null;
    this.erroDetalhe = false;
    this.mensagemAtualizacao = '';
    this.erroAtualizacao = '';
  }

  /** `true` quando as notas do rascunho respeitam a faixa 0–10. */
  notasValidas(disciplina: DisciplinaAluno): boolean {
    const rascunho = this.notasRascunho[disciplina.matricula_id];
    if (rascunho === undefined) {
      return false;
    }
    return [rascunho.nota_av1, rascunho.nota_av2, rascunho.nota_final].every(
      (nota) => nota === null || (Number.isFinite(nota) && nota >= 0 && nota <= 10),
    );
  }

  /** Lança as notas do rascunho no PATCH da API Admin (US4.2). */
  salvarNotas(disciplina: DisciplinaAluno): void {
    this.erroAtualizacao = '';
    this.mensagemAtualizacao = '';
    if (this.detalhe === null) {
      return;
    }
    if (!this.notasValidas(disciplina)) {
      this.erroAtualizacao = 'As notas devem estar entre 0 e 10.';
      return;
    }

    const rascunho = this.notasRascunho[disciplina.matricula_id];
    const payload: NotasMatriculaPayload = {
      nota_av1: rascunho.nota_av1,
      nota_av2: rascunho.nota_av2,
      nota_final: rascunho.nota_final,
      status_disciplina: rascunho.status_disciplina,
    };
    this.salvandoNotas[disciplina.matricula_id] = true;

    this.alunosService
      .lancarNotas(this.detalhe.aluno.id, disciplina.matricula_id, payload)
      .subscribe({
        next: (atualizada) => {
          disciplina.nota_av1 = atualizada.nota_av1;
          disciplina.nota_av2 = atualizada.nota_av2;
          disciplina.nota_final = atualizada.nota_final;
          disciplina.status_disciplina = atualizada.status_disciplina;
          this.salvandoNotas[disciplina.matricula_id] = false;
          this.mensagemAtualizacao = `Notas de ${disciplina.nome} atualizadas.`;
        },
        error: (erro: HttpErrorResponse) => {
          this.salvandoNotas[disciplina.matricula_id] = false;
          this.erroAtualizacao = this.mensagemErroAtualizacao(erro);
        },
      });
  }

  /** Altera o status do boleto selecionado no rascunho (US4.2). */
  salvarStatusMensalidade(mensalidade: MensalidadeAluno): void {
    this.erroAtualizacao = '';
    this.mensagemAtualizacao = '';
    const status = this.statusPagamentoRascunho[mensalidade.id];
    if (status === undefined || status === mensalidade.status_pagamento) {
      return;
    }

    this.salvandoMensalidade[mensalidade.id] = true;
    this.alunosService
      .alterarStatusMensalidade(mensalidade.id, status)
      .subscribe({
        next: (atualizada) => {
          mensalidade.status_pagamento = atualizada.status_pagamento;
          this.salvandoMensalidade[mensalidade.id] = false;
          this.mensagemAtualizacao = `Boleto ${
            mensalidade.mes_referencia
          } atualizado para ${this.rotuloStatusPagamento(
            atualizada.status_pagamento,
          )}.`;
        },
        error: (erro: HttpErrorResponse) => {
          this.salvandoMensalidade[mensalidade.id] = false;
          this.erroAtualizacao = this.mensagemErroAtualizacao(erro);
        },
      });
  }

  /** Altera o status de matrícula do aluno aberto no detalhe (US4.2). */
  salvarStatusMatricula(): void {
    this.erroAtualizacao = '';
    this.mensagemAtualizacao = '';
    if (this.detalhe === null) {
      return;
    }
    if (this.statusMatriculaSelecionado === this.detalhe.aluno.status_matricula) {
      return;
    }

    this.salvandoStatusMatricula = true;
    this.alunosService
      .alterarStatusMatricula(this.detalhe.aluno.id, this.statusMatriculaSelecionado)
      .subscribe({
        next: (aluno) => {
          if (this.detalhe !== null) {
            this.detalhe.aluno = aluno;
          }
          this.atualizarAlunoNaListagem(aluno);
          this.salvandoStatusMatricula = false;
          this.mensagemAtualizacao = `Matrícula atualizada para ${this.rotuloStatusMatricula(
            aluno.status_matricula,
          )}.`;
        },
        error: (erro: HttpErrorResponse) => {
          this.salvandoStatusMatricula = false;
          this.erroAtualizacao = this.mensagemErroAtualizacao(erro);
        },
      });
  }

  rotuloStatusMatricula(status: StatusMatricula): string {
    return ROTULO_STATUS_MATRICULA[status] ?? status;
  }

  rotuloStatusDisciplina(status: DisciplinaAluno['status_disciplina']): string {
    return ROTULO_STATUS_DISCIPLINA[status] ?? status;
  }

  rotuloStatusPagamento(status: StatusPagamento): string {
    return ROTULO_STATUS_PAGAMENTO[status] ?? status;
  }

  formatarValor(valor: number): string {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  formatarData(iso: string): string {
    const [ano, mes, dia] = iso.split('-');
    return `${dia}/${mes}/${ano}`;
  }

  formatarMes(mesReferencia: string): string {
    const [ano, mes] = mesReferencia.split('-');
    return `${mes}/${ano}`;
  }

  formatarNota(nota: number | null): string {
    return nota === null ? '—' : nota.toFixed(1);
  }

  rastrearAluno(_: number, aluno: AlunoResumo): string {
    return aluno.id;
  }

  rastrearDisciplina(_: number, disciplina: DisciplinaAluno): string {
    return disciplina.disciplina_id;
  }

  rastrearMensalidade(_: number, mensalidade: MensalidadeAluno): string {
    return mensalidade.id;
  }

  /** Copia o estado atual do detalhe para os rascunhos do simulador. */
  private inicializarSimulador(detalhe: AlunoDetalhe): void {
    this.statusMatriculaSelecionado = detalhe.aluno.status_matricula;
    this.notasRascunho = {};
    for (const disciplina of detalhe.disciplinas) {
      this.notasRascunho[disciplina.matricula_id] = {
        nota_av1: disciplina.nota_av1,
        nota_av2: disciplina.nota_av2,
        nota_final: disciplina.nota_final,
        status_disciplina: disciplina.status_disciplina,
      };
    }
    this.statusPagamentoRascunho = {};
    for (const mensalidade of detalhe.mensalidades) {
      this.statusPagamentoRascunho[mensalidade.id] = mensalidade.status_pagamento;
    }
  }

  /** Mantém a linha da listagem sincronizada com o detalhe editado. */
  private atualizarAlunoNaListagem(aluno: AlunoResumo): void {
    const indice = this.alunos.findIndex((item) => item.id === aluno.id);
    if (indice >= 0) {
      this.alunos[indice] = aluno;
    }
  }

  private mensagemErroAtualizacao(erro: HttpErrorResponse): string {
    if (erro.status === 403) {
      return 'Acesso negado. Apenas administradores podem alterar dados.';
    }
    if (erro.status === 404) {
      return 'Registro não encontrado. Recarregue o detalhe do aluno.';
    }
    if (erro.status === 422) {
      return 'Dados inválidos. Revise as notas e os status escolhidos.';
    }
    return 'Não foi possível atualizar o dado. Tente novamente.';
  }

  private mensagemErroCadastro(erro: HttpErrorResponse): string {
    if (erro.status === 409) {
      return 'CPF já cadastrado. Use outro CPF para o aluno fictício.';
    }
    if (erro.status === 403) {
      return 'Acesso negado. Apenas administradores podem cadastrar alunos.';
    }
    if (erro.status === 422) {
      return 'Dados inválidos. Revise os campos e tente novamente.';
    }
    return 'Não foi possível cadastrar o aluno. Tente novamente.';
  }

  private limparFormulario(): void {
    this.formulario.reset({
      nome_completo: '',
      cpf: '',
      email: '',
      telefone: '',
      curso: '',
      polo: '',
      status_matricula: 'ATIVO',
    });
  }
}
