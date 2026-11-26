import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import { cpfValidator } from '../../core/validators/cpf.validator';
import {
  AlunoDetalhe,
  AlunoResumo,
  CadastroAlunoPayload,
  DisciplinaAluno,
  MensalidadeAluno,
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

const ROTULO_STATUS_DISCIPLINA: Record<DisciplinaAluno['status_disciplina'], string> = {
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

type CampoFormulario =
  | 'nome_completo'
  | 'cpf'
  | 'email'
  | 'telefone'
  | 'curso'
  | 'polo'
  | 'status_matricula';

/**
 * Área admin de alunos — /admin/alunos (issues #16 e #17, US4.1).
 *
 * Lista alunos, busca por nome/CPF na API Admin e abre o detalhe com
 * disciplinas e mensalidades. O formulário de cadastro (#17) envia dados
 * fictícios para `POST /api/admin/alunos` e deixa o aluno consultável de
 * imediato pelo agente/teste E2E.
 */
@Component({
  selector: 'app-admin-alunos',
  imports: [FormsModule, ReactiveFormsModule],
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

  alunos: AlunoResumo[] = [];
  busca = '';
  carregando = false;
  erroListagem = false;

  detalhe: AlunoDetalhe | null = null;
  carregandoDetalhe = false;
  erroDetalhe = false;

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
    this.alunosService.detalhar(aluno.id).subscribe({
      next: (detalhe) => {
        this.detalhe = detalhe;
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
