Product Requirements Document (PRD): Assistente Académico EAD com RAG, Function Calling e Painel E2E
1. Visão Geral do Produto e Objetivos
O Assistente Académico EAD é um MVP de testes projetado para demonstrar a integração ponta a ponta (End-to-End) entre a inteligência artificial generativa (Azure AI Foundry), recuperação de conhecimento documental estático (RAG), execução de ações dinâmicas via API (Function Calling / Tools) e um painel de administração em tempo real.

Objetivos Principais
Validar Arquitetura Híbrida: Combinar conhecimento documental estático (calendário e regulamentos) com dados transacionais dinâmicos (notas, finanças, dados cadastrais).

Simular Experiência Real EAD: Permitir que o aluno consulte notas, emita declarações por e-mail e obtenha dados de pagamento no chat.

Ambiente de Testes Ágil (Painel Admin): Permitir a criação de novos alunos e alteração dinâmica de estados (notas, boletos) para validação imediata do comportamento do agente.

2. Personas e Casos de Utilizador
O Estudante EAD (Utilizador Final): Precisa de respostas rápidas sobre prazos académicos, consulta de notas por disciplina, obtenção de boletos e emissão imediata de declaração de matrícula.

O Administrador / Desenvolvedor (Testador): Precisa de um painel de controlo simples para simular o ciclo de vida do aluno, atualizar dados na base de dados em tempo real e inspecionar o comportamento do agente.

3. Arquitetura do Sistema e Stack Tecnológica
Camada de IA: Azure AI Foundry (Modelo GPT-4o, Grounding com dados estáticos em PDF/Markdown, Definições de Tools via OpenAPI).

Backend & API: Python (FastAPI) ou Node.js (Express), responsável por expor os endpoints das Tools e gerir as regras de negócio.

Base de Dados: Relacional (PostgreSQL ou SQLite para ambiente de testes).

Front-end: Interface web em React/Next.js (ou Streamlit/HTML estático) dividida em duas abas/módulos: Portal do Aluno (Chat + Dashboard) e Painel Administrativo (CRUD + Simulador).

4. Arquitetura e Modelagem de Dados (Schema Spec)
A base de dados suporta o mapeamento completo da jornada académica EAD:

4.1. Tabela: alunos
Guarda os dados cadastrais do estudante.

id (UUID / PK)

cpf (VARCHAR, Unique) – Chave de identificação primária.

nome_completo (VARCHAR)

email (VARCHAR) – Utilizado para o envio de documentos em PDF.

telefone (VARCHAR)

curso (VARCHAR)

polo (VARCHAR)

status_matricula (ENUM: ATIVO, TRANCADO, CONCLUIDO, INADIMPLENTE)

4.2. Tabela: disciplinas
Catálogo de unidades curriculares do curso EAD.

id (UUID / PK)

codigo (VARCHAR)

nome (VARCHAR)

semestre_ideal (INT)

4.3. Tabela: matriculas_disciplinas
Registo de desempenho, notas e progresso do aluno por disciplina.

id (UUID / PK)

aluno_id (FK -> alunos.id)

disciplina_id (FK -> disciplinas.id)

semestre_letivo (VARCHAR)

nota_av1 (FLOAT, Nullable)

nota_av2 (FLOAT, Nullable)

nota_final (FLOAT, Nullable)

status_disciplina (ENUM: EM_ANDAMENTO, APROVADO, REPROVADO, AGUARDANDO_NOTA)

4.4. Tabela: mensalidades
Gestão financeira e boletos.

id (UUID / PK)

aluno_id (FK -> alunos.id)

mes_referencia (VARCHAR)

valor_original (DECIMAL)

data_vencimento (DATE)

status_pagamento (ENUM: PENDENTE, PAGO, ATRASADO)

linha_digitavel (VARCHAR) – Código de barras simulado.

qr_code_pix (TEXT) – Chave Pix simulada.

4.5. Tabela: solicitacoes_documentos
Log de auditoria de documentos gerados pelo assistente.

id (UUID / PK)

aluno_id (FK -> alunos.id)

tipo_documento (VARCHAR)

enviado_para_email (VARCHAR)

data_emissao (TIMESTAMP)

5. Especificação de Endpoints da API (Tools / Function Calling)
O backend deve expor os seguintes contratos REST para serem mapeados nas Tools do Azure AI Foundry:

GET /api/aluno/status?cpf={cpf}

Descrição: Retorna as notas, frequências e status académico do aluno.

Retorno (JSON): Lista de disciplinas com respetivas notas e situação.

GET /api/financeiro/boleto?cpf={cpf}

Descrição: Consulta boletos pendentes. Escopo: ALUNO consulta apenas o próprio CPF;
ADMIN consulta qualquer CPF (painel administrativo e tools do Foundry).

Retorno (JSON): linha_digitavel, qr_code_pix, data_vencimento, status_pagamento.

POST /api/declaracoes/gerar

Payload (JSON): {"aluno_id": "uuid", "tipo": "matricula"}

Descrição: Compila o template HTML em PDF, envia por e-mail para o endereço registado do aluno e regista o log.

Retorno (JSON): {"status": "sucesso", "email_destino": "aluno@email.com"}

POST /api/admin/alunos (Painel Admin)

Payload (JSON): Dados cadastrais do novo aluno para injeção imediata no ambiente de testes.

6. Épicos e Histórias de Utilizador (Backlog para Desenvolvimento Ágil)
Épico 1: Infraestrutura de Dados & API (Backend)
US1.1: Modelação e criação da Base de Dados relacional (Tabelas de alunos, disciplinas, notas e mensalidades).

US1.2: Implementação dos Endpoints REST de consulta de notas, boletos e emissão de declarações em PDF com envio de e-mail.

US1.3: Criação do endpoint de registo de novos alunos para testes E2E (POST /api/admin/alunos).

Épico 2: Agente Azure AI Foundry & RAG Institucional
US2.1: Configuração do Agente no Azure AI Foundry com o modelo GPT-4o e carregamento de documentos estáticos (Calendário Académico e Regras).

US2.2: Registo dos schemas OpenAPI das funções (Function Calling) no assistente para interligação com os endpoints da API.

US2.3: Configuração do System Prompt institucional exigindo tom formal e verificação de parâmetros.

Épico 3: Módulo Front-end do Aluno
US3.1: Desenvolvimento do componente de Chat integrado via API com o Azure AI Foundry.

US3.2: Criação do Dashboard Académico visual para o aluno acompanhar notas e descarregar boletos diretamente.

Épico 4: Painel de Administração e Simulador (Admin)
US4.1: Criação do formulário de cadastro de novos alunos via interface web.

US4.2: Implementação de ferramentas de alteração em tempo real (lançamento de notas e alteração de status de boletos) para validação imediata do agente.

Épico 5: Observabilidade e Debug
US5.1: Painel de logs de Tool Calling no front-end para monitorizar em tempo real o payload enviado e recebido pelo agente.

7. Critérios de Aceitação e Teste E2E (Definição de Pronto)
O projeto será considerado validado com sucesso quando o seguinte ciclo E2E for executado sem falhas:

Um novo aluno é cadastrado via Painel Admin com dados fictícios.

O testador vai ao Chat do Aluno e pergunta sobre o calendário (respondido via RAG).

O testador pergunta a nota de uma disciplina recém-criada (o agente aciona a tool e devolve que ainda não foi lançada).

O administrador insere a nota no painel Admin.

O aluno repete a pergunta no chat e o agente reflete imediatamente a nova nota atualizada pela API.

O aluno pede o boleto e a declaração, recebendo o retorno estruturado e o e-mail respetivo.