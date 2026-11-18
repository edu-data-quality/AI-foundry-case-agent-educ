# ADR-0002: Ciclo de vida da sessão de chat (abertura, logout e timeout)

- **Data:** 2026-11-17
- **Status:** Aceito
- **Decisores:** time do projeto (issue #11)

## Contexto

O PRD exige rastreio ponta a ponta da jornada do aluno. O conteúdo das
mensagens fica nos traces do Azure AI Foundry; o banco precisa registrar
apenas o **ciclo de vida da sessão**: quando começou, quando terminou e por
quê (`LOGOUT` ou `TIMEOUT`).

A tabela `conversas` já existia desde a issue #2, mas sem regra de unicidade
nem referência de inatividade. Sem isso, um aluno podia acumular sessões
`ABERTA` e o timeout não tinha como medir "sem interação".

## Decisão

1. **Sessão aberta no login** — `POST /api/auth/login` chama
   `ConversaRepository.abrir_ou_continuar` para o aluno autenticado e devolve
   `conversa_id`. Fechamento explícito via `POST /api/auth/logout` com motivo
   `LOGOUT`.
2. **Uma ABERTA por aluno no banco** — índice único parcial em `conversas`:
   `uq_conversas_aluno_aberta (aluno_id) WHERE status = 'ABERTA'`. A regra
   deixa de ser só de aplicação e resiste a login concorrente. A migração
   `0002` fecha duplicatas legadas (mantém a mais recente, fecha as demais
   como `TIMEOUT`) antes de criar o índice.
3. **`ultima_interacao`** — coluna nova, atualizada por
   `abrir_ou_continuar` (login/reabertura). A integração do chat (S12) deve
   chamar `registrar_interacao` a cada mensagem para o timeout medir
   inatividade real, não o tempo desde o login.
4. **Job de timeout no lifespan da API** — varredura periódica
   (`THREAD_TIMEOUT_CHECK_SEGUNDOS`) fecha `ABERTA` sem interação há
   `THREAD_TIMEOUT_MIN` (default 10) com motivo `TIMEOUT`. O job sobe no
   `lifespan` do FastAPI e é cancelado no shutdown.
5. **Um varredor por deployment** — `THREAD_TIMEOUT_JOB_ATIVO` liga o job
   apenas no worker líder; os demais sobem com `0`. Sem isso, cada worker
   faria a mesma varredura (desperdício e contenção), ainda que a atualização
   condicional por status seja idempotente.

## Alternativas consideradas

- **Só regra na aplicação** para "uma ABERTA": rejeitada porque dois logins
  concorrentes passam juntos pelo `SELECT` e criam duas sessões. O índice
  parcial resolve no banco; o `IntegrityError` é tratado como "outro login
  venceu" e a sessão é retomada.
- **Scheduler externo (APScheduler/Celery beat)**: rejeitado no MVP; o
  lifespan do FastAPI cobre o caso com uma dependência a menos. Se o backend
  escalar para múltiplos processos, o controle de líder por env continua
  válido.
- **Lock de banco (`pg_advisory_lock`)** como líder automático: adiado; o
  ambiente de testes usa SQLite e não há ganho imediato sobre a variável de
  ambiente explícita.
- **Guardar mensagens no banco**: fora de escopo. O PRD define os traces do
  Foundry como fonte do conteúdo.

## Consequências

- **Positivas:** sessão única garantida no banco; timeout mede inatividade;
  auditoria de início/fim/motivo disponível por API; migração não quebra base
  legada.
- **Negativas:** o encerramento por timeout depende do job estar ligado em
  pelo menos um processo; a atualização por mensagem depende da S12 chamar
  `registrar_interacao`. Ambos estão documentados no código e nas variáveis
  de ambiente.