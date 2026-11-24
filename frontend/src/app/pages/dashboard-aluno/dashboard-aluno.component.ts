import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';

import { Boleto } from '../../models/boleto';
import { DisciplinaStatus, StatusAcademicoResposta, StatusDisciplina } from '../../models/status-academico';
import { FinanceiroService } from '../../services/financeiro.service';
import { SessaoAlunoService } from '../../services/sessao-aluno.service';
import { StatusAcademicoService } from '../../services/status-academico.service';

const ROTULO_STATUS_DISCIPLINA: Record<StatusDisciplina, string> = {
  EM_ANDAMENTO: 'Em andamento',
  APROVADO: 'Aprovado',
  REPROVADO: 'Reprovado',
  AGUARDANDO_NOTA: 'Aguardando nota',
};

const ROTULO_STATUS_PAGAMENTO: Record<string, string> = {
  PENDENTE: 'Pendente',
  PAGO: 'Pago',
  ATRASADO: 'Atrasado',
};

@Component({
  selector: 'app-dashboard-aluno',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard-aluno.component.html',
  styleUrl: './dashboard-aluno.component.css',
})
export class DashboardAlunoComponent implements OnInit {
  status: StatusAcademicoResposta | null = null;
  boletos: Boleto[] = [];
  erroCarregamento = false;
  boletoParaImprimir: Boleto | null = null;
  avisoDeclaracao = false;
  cpf: string | null = null;

  constructor(
    private readonly statusService: StatusAcademicoService,
    private readonly financeiroService: FinanceiroService,
    private readonly sessao: SessaoAlunoService,
  ) {}

  ngOnInit(): void {
    const cpf = this.sessao.cpf;
    if (!cpf) {
      this.erroCarregamento = true;
      return;
    }
    this.cpf = cpf;

    forkJoin({
      status: this.statusService.obterStatus(cpf),
      boletos: this.financeiroService.obterBoletos(cpf),
    }).subscribe({
      next: ({ status, boletos }) => {
        this.status = status;
        this.boletos = boletos;
      },
      error: () => {
        this.erroCarregamento = true;
      },
    });
  }

  get disciplinas(): DisciplinaStatus[] {
    return this.status?.disciplinas ?? [];
  }

  rotuloStatusDisciplina(status: StatusDisciplina): string {
    return ROTULO_STATUS_DISCIPLINA[status] ?? status;
  }

  rotuloStatusPagamento(status: string): string {
    return ROTULO_STATUS_PAGAMENTO[status] ?? status;
  }

  formatarData(iso: string): string {
    const [ano, mes, dia] = iso.split('-');
    return `${dia}/${mes}/${ano}`;
  }

  /** Ação "baixar boleto": abre a impressão do boleto selecionado. */
  baixarBoleto(boleto: Boleto): void {
    this.boletoParaImprimir = boleto;
    window.print();
  }

  /** Botão informativo: emissão real da declaração acontece na S14/chat. */
  pedirDeclaracao(): void {
    this.avisoDeclaracao = true;
  }
}
