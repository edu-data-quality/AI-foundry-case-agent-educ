/**
 * Modelos do contrato `GET /api/financeiro/boleto?cpf=` (issue #5).
 * Espelha o schema Pydantic BoletoResposta de backend/app/api/routes/financeiro.py.
 */

export type StatusPagamento = 'PENDENTE' | 'PAGO' | 'ATRASADO';

export interface Boleto {
  linha_digitavel: string | null;
  qr_code_pix: string | null;
  /** Data ISO (YYYY-MM-DD) serializada pelo backend. */
  data_vencimento: string;
  status_pagamento: StatusPagamento;
}
