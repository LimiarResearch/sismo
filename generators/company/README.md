# A simulated software company: 50 people running in time

The world is a whole company, with its systems working as real software, delivered minute by minute through the interface
described in `CONTRACT.md`. Nobody draws "events" on top of it: people work in the systems, customers use the product, the code
runs and the databases change. What goes out through the interface are measures of what the systems did. What the company really
has stays in `truth()`, separate, for the benchmark only.

The company is Brazilian. Everything the generator writes (process and field names, team names, ticket texts, event descriptions,
the keys and values in `verdade.json`) is data and stays in Portuguese; the glossary below translates the words used in process
and field names.

## Glossary

Words used in process names, field names and team names, with their English meaning.

| Portuguese | English | Portuguese | English |
|---|---|---|---|
| rota | route | chamado(s) | support ticket(s) |
| requisições | requests | respostas | responses |
| com erro | with an error | recusadas, recusas | refused, refusals |
| latência média / do percentil 95 | mean / 95th-percentile latency | clientes distintos | distinct customers |
| no minuto | in the minute | no dia, no mês | today, this month |
| servidor da aplicação | application server | uso de processador | CPU usage |
| memória em uso | memory in use | reinícios do processo | process restarts |
| banco do produto | product database | tamanho ocupado, espaço livre | size used, free space |
| consultas, escritas | queries, writes | instruções executadas em milhares | instructions executed, in thousands |
| fila de trabalhos | background job queue | pendentes, concluídos, falhas | pending, completed, failures |
| idade, mais antigo | age, oldest | gateway de pagamento, chamadas | payment gateway, calls |
| transportadoras, cotações de frete | carriers, shipping quotes | sonda de disponibilidade, verificações | availability probe, checks |
| implantação | deployment | tarefas agendadas do servidor | server scheduled jobs |
| linhas processadas | rows processed | enviados | sent |
| pedidos, itens, valor em reais | orders, items, value in BRL | pagamentos aprovados, pagos | payments approved, paid |
| notas fiscais, emitidas, emissões | fiscal notes (Brazilian tax invoices), issued, issuances | estoque, unidades repostas | stock, units restocked |
| sessões, iniciadas, abandonadas, ativas | sessions, started, abandoned, active | usuários conectados | connected users |
| faturamento, faturas, em aberto | billing, invoices, unpaid | estornos | refunds |
| região | region | carteira de clientes | customer base |
| entradas, saídas | joins, departures | cancelamentos, pedidos de cancelamento | cancellations, cancellation requests |
| plano básico, pro, empresarial | basic, pro, enterprise plan | pesquisa de satisfação, soma das notas | satisfaction survey, sum of scores |
| canal de atendimento, contatos recebidos | support channel, contacts received | telefone | phone |
| projeto Produto, Plataforma, Suporte, Infraestrutura | Product, Platform, Support, Infrastructure project | entrada, movimento, prazos, idade | intake, movement, deadlines, age |
| histórias, tarefas, épicos, bugs | stories, tasks, epics, bugs | backlog, refinamento, triagem | backlog, refinement, triage |
| prontos para desenvolver | ready for development | em desenvolvimento, em revisão, em qualidade | in development, in review, in QA |
| prontos para liberar, liberados | ready to release, released | em andamento, concluídos | in progress, completed |
| criados, transições, comentários | created, transitions, comments | reprovações, reaberturas, reabertos | rejections, reopenings, reopened |
| pontos planejados, do sprint, restantes | planned, sprint, remaining points | prioridade baixa, média, alta, crítica | low, medium, high, critical priority |
| abertos sem primeira resposta | open without a first response | aguardando cliente, escalados, resolvidos, fechados | waiting for customer, escalated, resolved, closed |
| fora do prazo, espera | past the deadline, wait | sob responsabilidade da equipe | owned by the team |
| fluxo da equipe de | workflow of the team | repositório de código, ramos abertos | code repository, open branches |
| linhas alteradas, revisões aprovadas | lines changed, approved reviews | revisões que pediram mudança | reviews that requested changes |
| código de, testes executados | code of, tests run | funil de vendas | sales funnel |
| qualificação, propostas, negociação | qualification, proposals, negotiation | ganhos, perdidos | won, lost |
| atividades de vendas, ligações | sales activities, calls | tarefas internas | internal tasks |
| leads de site, indicação, prospecção | leads from the website, referrals, prospecting | agenda da equipe | team calendar |
| pessoas em reunião, reuniões em curso | people in meetings, meetings in progress | reuniões do tipo | meetings of type |
| diária, planejamento, semanal, mensal | daily stand-up, planning, weekly, monthly | revisão e retrospectiva | review and retrospective |
| liderança, com cliente, entrevista, alinhamento | leadership, with a customer, interview, alignment | quadro da equipe, quadro geral | team staff board, overall staff board |
| pessoas no quadro, presentes agora | headcount, present now | em almoço, horas extras | at lunch, overtime hours |
| ausentes por férias, por falta | absent on vacation, absent (sick or missing) | vagas abertas, candidatos em processo | open positions, candidates in process |
| solicitações abertas à gestão | open requests to management | ponto, entradas e saídas registradas | time clock, recorded clock-ins and clock-outs |

Teams: produto (product), desenvolvimento (development), qualidade (quality assurance), atendimento (customer support), vendas
(sales), operação (operations), gestão (management). Components: login e conta (login and account), catálogo e busca (catalog and
search), pedido e carrinho (order and cart), frete (shipping), pagamento (payment), fiscal, relatórios (reports), notificações
(notifications), infraestrutura (infrastructure). Routes: login, catálogo (catalog), busca (search), produto (product page),
carrinho (cart), frete (shipping), pedido (order), pagamento (payment), relatório (report), exportação (export), notas fiscais
(fiscal notes), conta (account).

## What the world contains

**The product** (`product.py`, `codebase.py`). A purchasing platform for shops, with twelve routes: login, catalog, search,
product, cart, shipping, order, payment, report, export, fiscal notes and account. It has a real database (in-memory SQLite, with
customers, users, sessions, products, carts, orders, payments, fiscal notes, e-mails, invoices, a job queue and an audit log), a
background job queue (fiscal note, e-mail, invoice), jobs scheduled by the company clock (backup at 2:00, session cleanup at 3:00,
supplier restocking at 4:00, reindexing on Sundays, summary at 7:00, billing on the 1st) and a disk volume of limited size.

Each route calls functions. Each function has implementations written in `codebase.py`, and a product version is the choice of
one implementation per function. Some implementations have a defect, and the defect is genuinely wrong code. The function names
are recorded in the ground truth, so they stay in Portuguese:

| function | defect | how it shows up |
|---|---|---|
| normalizar_login | converts to ASCII | login breaks for users with an accented character in their user name |
| guardar_sessao | the cache never expires | memory grows until the process crashes |
| atualizar_conta | assumes a phone number | the account does not save for customers without a phone number |
| paginar | last-page cursor | the incomplete last page of the catalog breaks |
| normalizar_termo | converts to ASCII | search breaks on accented terms |
| ler_quantidade | one-digit input mask | cart and order break with 10 or more units |
| calcular_frete | CEP as a number | shipping and order break for postal codes starting with zero (São Paulo) |
| registrar_cobranca | does not check for an earlier payment | a double click charges twice (no error: it shows up in payments and, hours later, in tickets) |
| emitir_nota | tax table with only the South and Southeast | the fiscal note fails outside those regions and the queue grows; days later, tickets |
| montar_relatorio | reads every order | the report becomes slow and blows up when the table grows |
| exportar_csv | one query per order | the export becomes slow |
| enviar_email | uses only the trade name | the e-mail fails for customers without a trade name and the queue grows |

Other implementations are features. They do more (or less) work and permanently change the normal behavior of a route. There
are fourteen on the roadmap: catalog recommendations, anti-fraud on orders, paginated fiscal notes, search index, per-item report,
stronger passwords, two carriers for shipping, payer authentication, device registration, related products, forty items per page,
compressed export, synonym search and lighter recommendations. When the roadmap ends, it starts over as a revision.

Latency is a function of what the code did: round trips to the database, instructions the database executed (SQLite reports every
ten), application work, waiting for external services (payment gateway, carriers, anti-fraud) and CPU load. CPU and memory are also
a function of what the requests, jobs and scheduled jobs did and of what the process holds. An error is the exception actually
happening. When the volume fills up, every write fails with SQLite's own error ("database or disk is full") and the product goes
down.

**The repository** (`repository.py`). Commits swap the implementation of functions on each item's branch. The branch is merged
into main when quality approves. A version is built from main (regular release) or from the live version plus the fix (hotfix),
and a rollback returns to the previous version. Test runs and code reviews are also recorded here.

**The workflow tracker** (`workflow.py`), Jira-like, in SQLite. It has the projects Produto, Plataforma, Suporte and
Infraestrutura and items of type epic, story, task, bug and ticket, with per-type state, priority, component, owning team, points,
deadline, sprint, comments, item-version links, links between items (ticket escalated to a bug, bug caused by a story), reopenings
and the log of every transition with instant and team. Two-week sprints per project, with planning (goal and capacity) and a
retrospective. Counts per project, type, state, priority, component and team are kept by the database itself (triggers).

**The customers** (`customers.py`). They start as 380 to 440 shops, with a plan (básico, pro, empresarial), users, a CEP (postal
code), opening hours, usage intensity and satisfaction. Users open sessions during the shop's hours (more on Monday, less on
Friday, almost nothing at the weekend, more at the end of the month) and walk through purchase, browsing, management, account and
repeat-purchase journeys. Each step is a real call to the product. When the product fails, the user retries and gives up; minutes
later some open a ticket by chat, e-mail or phone. They also open tickets for questions, invoices, double charges and fiscal notes
that never arrived. They answer when support asks, pay their invoices, cancel when unhappy and answer the satisfaction survey.

**The 50 people** (`people.py`). Product (5), development (15, in two squads), quality (6), support (8), sales (8), operations (4)
and management (the owner, finance, HR and the office administrator). Each person has a role, a team, an arrival time, lunch,
a way of working, booked vacations, sick days, overtime and notice periods. What each role does is described at the top of
`people.py`. The chance that a commit brings a defect grows with the size of the item and with the squad's rush (how much is left
in the sprint compared with what can still be done). Rush also shortens testing and review.

**The calendar** (`agenda.py`): daily stand-ups per team, planning, refinement, review and retrospective per sprint, weekly team
meetings, leadership, a monthly meeting with the owner, customer meetings (demos and onboarding), interviews and alignment
meetings (post-incident, called by management or through the acts interface). Whoever is in a meeting does not act on the systems.

**The staff board** (`board.py`): people, time clock (recorded clock-ins and clock-outs), absences, overtime, open positions,
candidates, people joining and leaving, requests to management. **The CRM** (`crm.py`): deals from lead to won or lost,
activities, internal tasks.

**The clock** (`clock.py`): one instant per minute, starting on Monday, 1 June 2026. The processes live by the calendar (hour,
weekday, day of the month); in the "embaralhado" null variant that calendar is drawn in blocks.

**The interface** (`world.py`, `connectors.py`, `acts.py`): the `World` class of the contract, the connectors that read aggregates
from the systems, and the optional acts interface.

## What the company really has (and `truth()` records with instants)

- **Cycles.** The workday and the shops' hours; the busier Monday (more usage and tickets, including those held over the
  weekend); the slower Friday; releases on Tuesdays and Thursdays from 15:00; the end of the sprint (rush, an extra release on
  Friday, a burndown that reaches zero); the end of the month (more sales, more reports and orders, billing on the 1st); the
  server's nightly jobs and the Sunday reindexing.
- **Contingencies.** A release with a defect makes the route's errors rise within minutes; then the component's tickets arrive
  (human delay of minutes), then the escalations; finally the rollback (when the damage is large and came with the release) or the
  hotfix (when development reproduces and fixes it), and the return to normal. Silent defects (double charge, a growing queue, a
  slow query) arrive by other paths: queue and memory go up, tickets show up hours or days later. The infrastructure incident (the
  database volume fills up) takes the product down for tens of minutes and floods support; operations purges old audit rows and
  grows the volume with three to five weeks of headroom, and the cycle starts again.
- **Drift.** The customer base grows (about 1% per week, with steps at the end of the month) and with it usage, tickets, the
  database and CPU.
- **Regime changes.** The release that brings a feature changes the normal latency of a route for good (a step). A sprint planned
  above capacity (the owner makes a promise; a large customer asks for something) becomes a rush sprint, with overtime, more defects
  and less testing.

Each recording's `verdade.json` has all of this with instants: `ciclos` (with the instants of the sprint and month ends, or the
blocks of the shuffled calendar), `liberacoes`, `liberacoes_com_defeito`, `episodios_de_defeito_no_ar` (release, first error,
first ticket, first escalation, exit from production), `incidentes`, `mudancas_de_regime` (with the mean latency of the seven days
before and after), `deriva`, `sprints` and `sprints_de_pressa`, `defeitos_escritos`, `defeitos_barrados_antes_do_ar`, `pessoal`,
`chamados_por_causa` and `atos`.

## How to run it

Python 3.11 with numpy; the rest is the standard library (sqlite3). No network. From the repository root:

```python
from generators.company import World

m = World(1)                       # or World(1, "sem_defeito" | "embaralhado" | "sem_deriva" | "surdo")
for p in m.processes():
    print(p.name, p.fields)
values = m.step()                  # minute 1: {process: [values in field order]}
n = m.receive("operação", "pedido", "verifiquem a rota de frete")
...
for t, number, team, text in m.responses():
    ...
m.save("pause"); m = World.load("pause")
```

From the command line (as a module, or as a script from the repository root):

```
python -m generators.company.run <folder> <days> <seed> [null] [--acts file.csv]
python -m generators.company.check [minutes]          # checks the interface against the contract
python generators/company/run.py <folder> <days> <seed> [null] [--acts file.csv]
python generators/company/check.py [minutes]
```

`run.py` writes `minutos.csv.gz` (row `i` is minute `t = i`; header "process.field"), `processos.json`, `verdade.json`,
`eventos_humanos.csv`, `custo.json` and, with acts, `atos.csv` and `respostas.csv`. The acts file has the header
`t,equipe,tipo,texto`; there is an example in `acts_example.csv`. That example is kept in Portuguese on purpose: the team names and
the act kinds ("pergunta", "pedido", "convocacao") are the values the interface accepts, and the text is matched against
Portuguese route keywords to find the route or component an act is about.

## How to produce your own recording

Each recording is a folder written by `run.py`. For example, a normal company, the four null variants and a run with the
example acts, all with seed 1:

```
python -m generators.company.run recordings/normal_90_days 90 1
python -m generators.company.run recordings/sem_defeito_30_days 30 1 sem_defeito
python -m generators.company.run recordings/embaralhado_30_days 30 1 embaralhado
python -m generators.company.run recordings/sem_deriva_30_days 30 1 sem_deriva
python -m generators.company.run recordings/surdo_30_days 30 1 surdo --acts generators/company/acts_example.csv
python -m generators.company.run recordings/acts_30_days 30 1 --acts generators/company/acts_example.csv
```

The same seed always gives the same recording. The "surdo" variant accepts the acts and nothing changes, so its minutes are the
same as those of the normal company with the same seed. A run with acts records the responses with their instants; compared with
the normal company with the same seed, it shows the effect of the acts (meetings, checks, focus changes and rollbacks that would
not have happened on their own).

To look at a recording against its ground truth, with simple numbers (cycle per hour and per weekday, correlation with the
previous day and week, customer base, each release with a defect, each incident, each regime change):

```
python -m generators.company.viewer recordings/normal_90_days
python generators/company/viewer.py recordings/normal_90_days
```

## What each team does with each act

The act becomes an item in the team's system on the next step and enters the team's queue like any other item. Whoever is free in
the team (during working hours, outside meetings, between tasks) takes the first one in the queue and spends time on it: 10 to 25
minutes on a question, 30 to 80 on a request, 5 to 12 to schedule a meeting call. Urgent items (critical bug, incident) go first.
Anything not handled by the end of working hours on the next workday goes unanswered.

| team | where the act becomes an item | question: the response says | request: the team does |
|---|---|---|---|
| operação | task in the Infraestrutura project | live version and for how long; requests, errors and latency of the mentioned route in the last half hour; free space on the database volume; job queue | runs the full test suite of the route's component against the live version; if something fails, opens a critical bug and, if the failure came with the last release, rolls back to the previous version |
| qualidade | task in the project of the mentioned component | items waiting for testing; runs, tests and failures in the last 24 hours | reruns the component's tests on the live version; if they fail, opens a bug and reopens the story that caused the failure |
| desenvolvimento | task in the project of the mentioned component | items in progress and in review; open bugs of the component | raises the component's open bug to critical (someone drops what they are doing and takes it) or, if there is no bug, runs the tests and opens a critical one if something fails |
| atendimento | ticket in the Suporte project | open tickets and tickets without a first response; open and escalated tickets of the component | answers the component's tickets first for the next four hours |
| produto | task in the Produto project | stories in the backlog, in refinement and ready | records a story with the act's text, high priority |
| vendas | internal task in the CRM | deals in each funnel stage; deals won in the last seven days | goes back first to the stalled proposals and negotiations for the next two days |
| gestão | request on the staff board | people, present, on vacation, open positions, candidates, active customers | management schedules an alignment meeting of the team leads at the first free slot |

A meeting call, for any team, becomes a 30-minute meeting ("alinhamento") with every person in the team at the first working-hours
slot in which all of them are free; the response gives the day and time. Whoever is in it does not act on the systems while it
lasts.

An act has a real cost: the person handling it stops doing something else, the meeting takes the team away from the systems, a
request to operations can roll a version back, the support focus delays the other tickets.

With seed 1 and the 22 acts of `acts_example.csv` over 30 days:

- pergunta (question): 9 answered; median delay of 27 minutes (from 10 to 89).
- pedido (request): 10 answered; median delay of 62 minutes (from 35 to 127).
- convocacao (meeting call): 3 answered; median delay of 26 minutes (from 13 to 60).
- unanswered: 0 of 22.

## Processes and fields

There are 131 processes and 495 fields, always in the same order. "No minuto" (in the minute) means what happened in that minute;
the other fields are the state in that minute. No field is a normal/abnormal label and none comes from a single person.

**rota** (route). One per product route. Requests in the minute (from users and from the operations probe, which calls each route
once per minute with test data); responses with an error (an exception in the code, a restarting process, a full database);
responses refused by the business rules (out of stock, card declined, order already paid, unknown login); mean and 95th-percentile
latency in milliseconds, computed from the work the code did; distinct customers that called the route (excluding the monitoring
account).

- `rota login`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota catálogo`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota busca`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota produto`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota carrinho`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota frete`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota pedido`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota pagamento`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota relatório`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota exportação`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota notas fiscais`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota conta`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto

**servidor da aplicação** (application server). CPU usage (work of the requests, the queue and the scheduled jobs), process memory
(base, session cache, queue, error log, rows loaded in the minute) and restarts (release or crash for lack of memory).

- `servidor da aplicação`: uso de processador em %; memória em uso em MB; reinícios do processo no minuto

**banco do produto** (product database). Size used by the database (4 KB pages in use), free space on the volume, queries and
writes in the minute, and instructions the database executed, in thousands.

- `banco do produto`: tamanho ocupado em MB; espaço livre no volume em MB; consultas no minuto; escritas no minuto; instruções executadas em milhares

**fila de trabalhos** (job queue). The background queue (fiscal notes, e-mails, invoices): pending, completed and failed jobs in
the minute, and the age of the oldest pending job.

- `fila de trabalhos`: trabalhos pendentes; trabalhos concluídos no minuto; falhas de trabalho no minuto; idade do trabalho pendente mais antigo em minutos

**gateway de pagamento** (payment gateway). Calls to the payment route and card refusals in the minute.

- `gateway de pagamento`: chamadas no minuto; recusas no minuto

**transportadoras** (carriers). Shipping quotes requested by customers in the minute and those that ended in an error.

- `transportadoras`: cotações de frete no minuto; cotações com erro no minuto

**sonda de disponibilidade** (availability probe). The operations checks (one per route per minute) and how many failed.

- `sonda de disponibilidade`: verificações no minuto; verificações com falha no minuto

**implantação** (deployment). Deployments in the minute (release, hotfix or rollback), and the commits and items that came with
them.

- `implantação`: implantações no minuto; commits incluídos no minuto; itens incluídos no minuto

**tarefas agendadas do servidor** (server scheduled jobs). Scheduled jobs running and the rows they processed in the minute.

- `tarefas agendadas do servidor`: tarefas em execução; linhas processadas no minuto

**e-mails do produto** (product e-mails). E-mails sent and failed in the minute.

- `e-mails do produto`: enviados no minuto; com falha no minuto

**pedidos** (orders). Orders created in the minute, their value and number of items.

- `pedidos`: pedidos criados no minuto; valor dos pedidos no minuto em reais; itens nos pedidos do minuto

**pagamentos** (payments). Payments approved, distinct orders paid and payments refused in the minute.

- `pagamentos`: pagamentos aprovados no minuto; pedidos pagos no minuto; pagamentos recusados no minuto

**notas fiscais** (fiscal notes). Fiscal notes issued and failed issuances in the minute.

- `notas fiscais`: notas emitidas no minuto; emissões com falha no minuto

**estoque** (stock). Products out of stock and units restocked by suppliers in the minute.

- `estoque`: produtos sem estoque; unidades repostas no minuto

**sessões dos clientes** (customer sessions). Sessions opened in the minute, sessions abandoned after an error, active sessions and
connected users.

- `sessões dos clientes`: sessões iniciadas no minuto; sessões abandonadas depois de erro no minuto; sessões ativas; usuários conectados

**faturamento** (billing). Invoices issued and paid in the minute, unpaid invoices, refunds made by finance in the minute.

- `faturamento`: faturas emitidas no minuto; faturas pagas no minuto; faturas em aberto; estornos feitos no minuto

**região** (region). One per CEP region: active customers, orders, shipping quotes and failed quotes in the minute.

- `região São Paulo`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Rio de Janeiro e Espírito Santo`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Minas Gerais`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Norte e Nordeste`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Centro-Oeste`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Sul`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto

**carteira de clientes** (customer base). Active customers, joins and cancellations in the minute, cancellation requests still open
with management.

- `carteira de clientes`: clientes ativos; entradas no minuto; cancelamentos no minuto; pedidos de cancelamento abertos

**clientes do plano** (customers on a plan). One per plan: active customers, active sessions, orders and tickets opened in the
minute.

- `clientes do plano básico`: clientes ativos; sessões ativas; pedidos no minuto; chamados abertos no minuto
- `clientes do plano pro`: clientes ativos; sessões ativas; pedidos no minuto; chamados abertos no minuto
- `clientes do plano empresarial`: clientes ativos; sessões ativas; pedidos no minuto; chamados abertos no minuto

**pesquisa de satisfação** (satisfaction survey). Survey responses after a ticket is closed and the sum of the scores (1 to 5) in
the minute.

- `pesquisa de satisfação`: respostas no minuto; soma das notas no minuto

**canal de atendimento** (support channel). One per channel: contacts received in the minute.

- `canal de atendimento chat`: contatos recebidos no minuto
- `canal de atendimento e-mail`: contatos recebidos no minuto
- `canal de atendimento telefone`: contatos recebidos no minuto

**projeto Produto** (Product project). The development projects in the workflow tracker. Entrada (intake): stories in the backlog
and in refinement, open bugs, epics in progress, tasks in the backlog. Desenvolvimento (development): items in each stage.
Movimento (movement): creations, transitions, releases, rejections (from review and from quality), reopenings and comments in the
minute. Sprint: items, planned points (goal), sprint points, completed and remaining points, high or critical priority items.
Prioridades (priorities): open items by priority. Idade (age): open items and their mean age in hours.

- `projeto Produto: entrada`: histórias no backlog; histórias em refinamento; bugs abertos ou em triagem; épicos em andamento; tarefas no backlog
- `projeto Produto: desenvolvimento`: prontos para desenvolver; em desenvolvimento; em revisão; em qualidade; prontos para liberar
- `projeto Produto: movimento`: itens criados no minuto; transições no minuto; itens liberados no minuto; reprovações no minuto; reaberturas no minuto; comentários no minuto
- `projeto Produto: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Produto: prioridades`: itens abertos de prioridade baixa; itens abertos de prioridade média; itens abertos de prioridade alta; itens abertos de prioridade crítica
- `projeto Produto: idade`: itens abertos; idade média dos itens abertos em horas

**projeto Plataforma** (Platform project). The same fields, for the Plataforma project.

- `projeto Plataforma: entrada`: histórias no backlog; histórias em refinamento; bugs abertos ou em triagem; épicos em andamento; tarefas no backlog
- `projeto Plataforma: desenvolvimento`: prontos para desenvolver; em desenvolvimento; em revisão; em qualidade; prontos para liberar
- `projeto Plataforma: movimento`: itens criados no minuto; transições no minuto; itens liberados no minuto; reprovações no minuto; reaberturas no minuto; comentários no minuto
- `projeto Plataforma: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Plataforma: prioridades`: itens abertos de prioridade baixa; itens abertos de prioridade média; itens abertos de prioridade alta; itens abertos de prioridade crítica
- `projeto Plataforma: idade`: itens abertos; idade média dos itens abertos em horas

**projeto Infraestrutura** (Infrastructure project). The operations project: tasks and bugs by state, movement, sprint, priorities
and age.

- `projeto Infraestrutura: itens`: tarefas no backlog; tarefas prontas; em andamento; bugs abertos; concluídos no minuto
- `projeto Infraestrutura: movimento`: itens criados no minuto; transições no minuto; comentários no minuto
- `projeto Infraestrutura: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Infraestrutura: prioridades`: itens abertos de prioridade baixa; itens abertos de prioridade média; itens abertos de prioridade alta; itens abertos de prioridade crítica
- `projeto Infraestrutura: idade`: itens abertos; idade média dos itens abertos em horas

**projeto Suporte** (Support project). Support in the workflow tracker: tickets by state, movement (new, first responses, resolved,
closed, reopened, comments), deadlines (past the first-response deadline, wait of the oldest ticket without a response),
priorities, sprint and age.

- `projeto Suporte: chamados por estado`: abertos sem primeira resposta; em atendimento; aguardando cliente; escalados; resolvidos aguardando fechamento
- `projeto Suporte: movimento`: chamados novos no minuto; primeiras respostas no minuto; resolvidos no minuto; fechados no minuto; reabertos no minuto; comentários no minuto
- `projeto Suporte: prazos`: chamados fora do prazo de primeira resposta; espera do chamado mais antigo sem resposta em minutos
- `projeto Suporte: prioridades`: chamados abertos de prioridade baixa; chamados abertos de prioridade média; chamados abertos de prioridade alta; chamados abertos de prioridade crítica
- `projeto Suporte: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Suporte: idade`: chamados abertos; idade média dos chamados abertos em horas

**chamados de** (tickets for). One per component: open tickets, new in the minute, escalated, resolved in the minute.

- `chamados de login e conta`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de catálogo e busca`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de pedido e carrinho`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de frete`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de pagamento`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de fiscal`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de relatórios`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de notificações`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de infraestrutura`: abertos; novos no minuto; escalados; resolvidos no minuto

**bugs de** (bugs of). One per component: open bugs, created and released in the minute.

- `bugs de login e conta`: abertos; criados no minuto; liberados no minuto
- `bugs de catálogo e busca`: abertos; criados no minuto; liberados no minuto
- `bugs de pedido e carrinho`: abertos; criados no minuto; liberados no minuto
- `bugs de frete`: abertos; criados no minuto; liberados no minuto
- `bugs de pagamento`: abertos; criados no minuto; liberados no minuto
- `bugs de fiscal`: abertos; criados no minuto; liberados no minuto
- `bugs de relatórios`: abertos; criados no minuto; liberados no minuto
- `bugs de notificações`: abertos; criados no minuto; liberados no minuto
- `bugs de infraestrutura`: abertos; criados no minuto; liberados no minuto

**fluxo da equipe** (team workflow). One per team: open items owned by the team, transitions, comments and items created by the
team in the minute.

- `fluxo da equipe de produto`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de desenvolvimento`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de qualidade`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de atendimento`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de vendas`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de operação`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de gestão`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto

**épicos** (epics). Epics open, in progress and completed in the minute.

- `épicos`: abertos; em andamento; concluídos no minuto

**repositório de código** (code repository). Commits, lines changed, approved reviews and reviews that requested changes in the
minute, and open branches.

- `repositório de código`: commits no minuto; linhas alteradas no minuto; revisões aprovadas no minuto; revisões que pediram mudança no minuto; ramos abertos

**código de** (code of). One per component: commits, tests run and failed tests in the minute (quality, development, operations).

- `código de login e conta`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de catálogo e busca`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de pedido e carrinho`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de frete`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de pagamento`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de fiscal`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de relatórios`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de notificações`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de infraestrutura`: commits no minuto; testes executados no minuto; testes com falha no minuto

**funil de vendas** (sales funnel). Deals in each stage, won and lost in the minute, open annual value in thousands of BRL.

- `funil de vendas`: leads; em qualificação; propostas; em negociação; ganhos no minuto; perdidos no minuto; valor em aberto em milhares de reais

**atividades de vendas** (sales activities). Calls, e-mails and proposals sent in the minute, open internal tasks.

- `atividades de vendas`: ligações no minuto; e-mails no minuto; propostas enviadas no minuto; tarefas internas abertas

**leads de** (leads from). One per source (site, indicação, prospecção): new leads in the minute and open deals from that source in
the funnel.

- `leads de site`: novos no minuto; em aberto no funil
- `leads de indicação`: novos no minuto; em aberto no funil
- `leads de prospecção`: novos no minuto; em aberto no funil

**agenda da equipe** (team calendar). One per team: people in a meeting now, team meetings in progress, person-minutes of meetings
accumulated in the day.

- `agenda da equipe de produto`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de desenvolvimento`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de qualidade`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de atendimento`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de vendas`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de operação`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de gestão`: pessoas em reunião; reuniões em curso; minutos de reunião no dia

**reuniões do tipo** (meetings of type). One per meeting type: meetings in progress and the people in them.

- `reuniões do tipo diária`: em curso; pessoas
- `reuniões do tipo planejamento`: em curso; pessoas
- `reuniões do tipo refinamento`: em curso; pessoas
- `reuniões do tipo revisão e retrospectiva`: em curso; pessoas
- `reuniões do tipo semanal`: em curso; pessoas
- `reuniões do tipo liderança`: em curso; pessoas
- `reuniões do tipo mensal`: em curso; pessoas
- `reuniões do tipo com cliente`: em curso; pessoas
- `reuniões do tipo entrevista`: em curso; pessoas
- `reuniões do tipo alinhamento`: em curso; pessoas

**quadro da equipe** (team staff board). One per team: headcount, present now (clocked in), at lunch, absent on vacation and absent
(sick) today, overtime hours in the day.

- `quadro da equipe de produto`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de desenvolvimento`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de qualidade`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de atendimento`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de vendas`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de operação`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de gestão`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia

**quadro geral** (overall staff board). Headcount, joins and departures in the month, open positions, candidates in process, open
requests to management.

- `quadro geral`: pessoas no quadro; entradas no mês; saídas no mês; vagas abertas; candidatos em processo; solicitações abertas à gestão

**ponto** (time clock). Clock-ins and clock-outs recorded in the minute.

- `ponto`: entradas registradas no minuto; saídas registradas no minuto

## Cost

The world takes a few seconds of machine time per simulated day (about 4 to 7 seconds, depending on the machine and on how many
runs share it) and uses less than 150 MB of memory; the minute gets slightly more expensive over time as the customer base and the
database grow. The contract asks for 30 days in under 10 minutes and 90 days in under 30, below 2 GB. Each run writes its own
figures to `custo.json`.

## What was left out

- **Real network and servers.** Routes are function calls inside the process; latency is computed from the work the code did
  (database instructions, database round trips, application work, waiting for external services, CPU load), not measured on the
  machine's clock, so that the same seed repeats the same life. `World(seed, real_time=True)` makes each step wait for the
  corresponding wall-clock minute, so the simulation can be run at real speed.
- **External services** (payment gateway, carriers, anti-fraud) and leads arriving through the website are random: they are the
  outside world, not the company.
- **Holidays, time zones and daylight saving time** do not exist; the calendar starts on 1 June 2026 and follows the Gregorian
  calendar.
- **A single infrastructure incident mode** (the database volume filling up). Network, certificates, machines and providers do not
  fail. Short process crashes happen while the memory defect is live; the ground truth lists them separately.
- **People without names and without a life outside work.** They have an identifier, a role, working hours and a way of working;
  decisions are rules with randomness, without learning. Salary, performance reviews and conflict do not exist.
- **Quality's tests** are a small, fixed suite per function (34 tests); coverage is which of them run. Performance tests exist only
  for the report and the export.
- **Marketing, finance beyond invoices and refunds, and purchasing** are left out. Stock is restocked by the suppliers overnight.
- **Responses to acts** are sentences built from the numbers in the systems; there is no free conversation.
- **The same life on another machine** depends on the same versions of Python, numpy and SQLite: SQLite's instruction count can
  change between versions. On the same machine the same seed repeats the same life (also checked across processes).
- **The shuffled null variant** draws the calendar in blocks of 25 to 240 minutes; inside a block the calendar runs normally (a
  15-minute stand-up still lasts 15 minutes), but nothing repeats periodically on the interface clock.
- **Runs longer than a year** work, but the feature roadmap and the vacations were designed for the first months; after the
  roadmap, the features come back as revisions.
