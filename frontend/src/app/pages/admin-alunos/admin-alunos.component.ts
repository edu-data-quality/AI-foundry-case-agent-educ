import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  AlunoDetalhe,
  AlunoResumo,
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

/**
 * Área admin de alunos — /admin/alunos (issue #16, US4.1).
 *
 * Lista alunos, busca por nome/CPF na API Admin e abre o detalhe com
 * disciplinas e mensalidades; base para o cadastro e o simulador do Épico 4.
 */
@Component({
  selector: 'app-admin-alunos',
  imports: [FormsModule],
  templateUrl: './admin-alunos.component.html',
  styleUrl: './admin-alunos.component.css',
})
export class AdminAlunosComponent implements OnInit {
  alunos: AlunoResumo[] = [];
  busca = '';
  carregando = false;
  erroListagem = false;

  detalhe: AlunoDetalhe | null = null;
  carregandoDetalhe = false;
  erroDetalhe = false;

  constructor(private readonly alunosService: AdminAlunosService) {}

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
}
