# The world contract: the interface through which the company delivers what happens

The world is a process in time. Everything that goes in or out of it passes through the interface described here.

The company is Brazilian, so everything the world produces (process names, field names, team names, ticket texts, event
descriptions, ground-truth keys) is in Portuguese. `README.md` has a glossary.

## The World class (generators/company/world.py)
- `World(seed: int, null: str | None = None, real_time: bool = False)`: builds the whole company from the seed (same seed, same
  company). `null` switches on one of the null variants: "sem_defeito" (no release carries a defect), "embaralhado" (the
  processes' time has no cycles), "sem_deriva" (the customer base does not grow), "surdo" (acts are accepted and ignored; see
  below).
- `world.processes() -> list[Process]`: the fixed list of observable processes, each with a `name` (readable, unique) and
  `fields` (a list of readable field names). Between one hundred and three hundred processes, each with one to eight numeric
  fields. No field may be the ground truth in disguise (a field "there was a release with a defect" would give the answer away).
- `world.step() -> dict[str, list[float]]`: makes one minute happen (people act, customers hit the product, the code runs, the
  databases change) and returns, for each process by name, the values of its fields in that minute, in the order of `fields`. One
  minute per call, always the next one. The caller calls `step()` when it is ready for the next minute; the world never moves by
  itself.
- `world.t`: the current minute (an integer, starting at 0). `world.day()`, `world.minute_of_day()`, `world.day_of_week()`
  (0 = Monday).
- `world.save(folder)` and `World.load(folder)`: pause and resume; the whole state (the databases, the agents, the clock) goes to
  the folder and comes back unchanged.
- `world.truth() -> dict`: what the company really has and when it happened (cycles, releases and which ones carried a defect,
  incidents, new versions, drift, rush sprints), with instants. It is for the benchmark only; a method under evaluation must
  not read it.
- `world.human_events() -> list[tuple[int, str]]`: one row per event that a person in the company would notice (release,
  incident, hotfix, hire), with its instant; for reading alongside a recording.

## What does not go through the interface
No text about what matters. No "normal" or "abnormal" label. No data about individual people: only aggregates by team, project,
queue, route, stage, calendar, staff board and customer base.

## Clarifications
- **The clock.** `t = 0` is the creation of the company (Monday, midnight). Each `step()` advances `t` and makes minute `t`
  happen; the returned values, `day()`, `minute_of_day()`, `day_of_week()` and the instants in `truth()` all refer to that same
  `t`. Thirty days go from `t = 1` to `t = 43,200`.
- **`Process`** has `name` and `fields` and nothing else. The list does not change while the world runs.
- **Null variant "embaralhado" (shuffled).** The company lives by an internal calendar drawn in blocks of variable length (25 to
  240 minutes); each block gets a random hour, weekday and day of the month, and inside the block the calendar runs minute by
  minute. People, customers, meetings, releases and the server's scheduled jobs follow that calendar; durations and
  cause-and-effect delays follow the real minute. Every hourly, weekly, sprint and monthly cycle disappears; the world still
  advances one minute per call and never by itself. `truth()` records the drawn calendar: the blocks, with start, end and the
  hour, weekday and day of the month each one received. The interface clock (`t`, `day()`...) stays real.
- **Null variant "sem_defeito" (no defect).** No release with a defect reaches production: people still write defects, but
  quality runs the full test suite and blocks all of them. The infrastructure incident remains (it is not a release); the ground
  truth marks it as the only episode of errors followed by tickets in this variant.
- **Null variant "sem_deriva" (no drift).** Only the customer base stops growing: each customer that joins leads to the most
  dissatisfied customer leaving within two days. New versions still change latency; in `truth()` they appear as "regime change"
  (a step with an instant), separate from "drift" (what grows slowly).
- **Priority may go out** through the interface (counts of items and tickets by priority), because it is what people put in the
  systems. No alert field goes out, nor any field computed to say that something is out of the ordinary.
- **The owner and the office administrator** form the "gestão" (management) team in the aggregates; no aggregate comes from a
  single person.
- **The laws repeat.** Incidents, versions that change latency and rush sprints happen by the laws of the world, not by a
  schedule: the database volume fills up with use and operations gives it three to five weeks of headroom each time; the features
  of the epics change the work of a route in part of the releases; a rush sprint appears when the plan exceeds capacity. In the
  first 30 days each of them happens at least once (the initial state of the company makes sure of it) and in 90 days each one
  repeats.

## Acts: optional scenario injection
Acts are an optional interface for injecting scenarios: questions, requests and meeting calls sent to the company's teams. An
act becomes something inside the world, people handle it as they handle everything else, and the response comes back through the
interface with a human delay.
- `world.teams() -> list[str]`: the team names ("produto", "desenvolvimento", "qualidade", "atendimento", "vendas", "operação",
  "gestão").
- `world.receive(team: str, kind: str, text: str) -> int`: registers an act for the team. `kind` is "pergunta" (question),
  "pedido" (request) or "convocacao" (meeting call). Returns the act number (the reference the created item carries in the team's
  system). The act happens on the next `step()`: it becomes an item in the workflow tracker (product, development, quality,
  operations), a support ticket, a task in the sales CRM, or a request to management. Inside the world the origin of these items
  is called "porta"; in the aggregates they are ordinary items (queue, open, age). The text is matched against Portuguese route
  keywords to find the route or component it is about.
  - "pergunta": someone in the team handles the item in queue order, during working hours and outside meetings, between tasks; the
    response is a short text built from what the team's systems show at that moment, never the ground truth.
  - "pedido": like a question, but the team acts: operations runs the route's tests against the live version and, if they fail,
    rolls back (if the failure came with the last release) or opens a fix with critical priority; quality reruns the tests on the
    live version and reopens the item that caused the failure; support answers the component's tickets first for the next four
    hours; development raises the component's bug to critical or looks for the failure; product records the story; sales goes
    back to the stalled proposals; management schedules an alignment meeting of the team leads.
  - "convocacao": becomes a meeting on the team's calendar at the first slot in which everyone is free; whoever is in it does not
    act on the systems while it lasts; the response says when the meeting was scheduled.
  Each act takes people's time; many acts slow the team down (the queue grows, deadlines slip), with no explicit penalty.
- `world.responses() -> list[tuple[int, int, str, str]]`: the responses that arrived since the last call, as
  `(t, act number, team, text)`. An act not handled by the end of working hours on the next workday goes unanswered.
- Null variant **"surdo" (deaf)**: `receive()` accepts and returns a number, and nothing happens; `responses()` stays empty.
- `python -m generators.company.run <folder> <days> <seed> [null] [--acts file.csv]`: the acts file has the header
  `t,equipe,tipo,texto` (minute, team, kind, text); the act on row `t` is delivered right before the step that makes minute `t`.
  Responses are recorded with their instants in `respostas.csv`.

## Recordings
`run.py` writes `minutos.csv.gz`: one row per minute (row `i` after the header is minute `t = i`), with the values in the order of
`processes()` and of `fields`; the first row has the names "process.field".

## Cost
Thirty days (43,200 calls to `step()`) in under ten minutes of machine time and ninety days (129,600 calls) in under thirty, below
2 GB of memory. Python 3.11; numpy and sqlite3 (standard library). No network.
