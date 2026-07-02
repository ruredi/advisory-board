# Advisory Board

Status: concept and implementation brief  
Owner: Andras Polgar  
Created: 2026-06-29  
Project folder: `advisory-board`  
Primary interface: channel-agnostic advisor identities + Jenny / OpenClaw summary interface

## Purpose

The Advisory Board is a standalone strategic decision system that can expose distinct advisor identities across multiple communication channels, while Jenny and OpenClaw can still call it for summaries and quick private decisions.

The system is not a worker-agent team. The advisors do not execute tasks, run long-running goals, autonomously change themselves, or self-improve. They are stable thinking lenses that Andras or Jenny can call when a decision needs sharper strategy, product judgment, revenue thinking, capital discipline, or decision hygiene.

The core idea:

- Jenny remains the main front door, not the owner of the advisors.
- Andras can ask Jenny normally from any supported channel.
- Jenny can call the board when a decision needs multiple strategic perspectives.
- Andras can also talk to individual advisors directly.
- Hermes can host advisors as separated channel-facing profiles.
- Telegram is only one channel, not the product boundary.
- Other channels can be added later without changing the advisor core.
- OpenClaw/Jenny can call the board through an adapter layer.
- Marveen remains the worker-agent environment for execution tasks.
- New source material, such as podcasts, interviews, books, shareholder letters, and transcripts, can be added to the knowledge base over time.

## Core Decision

Build a custom Advisory Board system as a separate project with a runtime-agnostic advisor core and a channel-agnostic interface model.

Do not bake the advisors into Jenny. Jenny should be able to talk to them, but Andras should also be able to talk to them directly.

Do not use Marveen as the board runtime. Marveen is useful for worker agents, such as research, development, sales, content, and ops. Those agents execute. The advisors think.

Do not use NotebookLM as the main runtime. NotebookLM is strong as a research workbench for large source sets, but it is too closed and too indirect to be the operating brain of the board.

Runtime decision:

- OpenClaw is stronger for Jenny integration and fast MVP.
- Hermes is stronger for separated advisor identities and dedicated direct chat channels.
- Current recommendation: keep the advisor core runtime-agnostic, but build the Hermes identity/profile layer early because separate advisor presences are the desired product experience.
- Keep OpenClaw/Jenny as the central personal assistant, quick orchestrator, and summary interface.

Detailed docs:

- `docs/runtime-comparison.md`
- `docs/channel-advisory-board-ux.md`
- `docs/direct-advisor-chat.md`
- `docs/telegram-direct-advisors.md`

Use Hermes as the first identity/interface layer because it is better suited for:

- one profile per advisor
- direct private chat with individual advisors
- a shared private Advisory Board room where the chosen channel supports multi-party discussion
- clearer profile/state separation
- a separate Moderator profile for formal board sessions

Keep the advisor core portable because OpenClaw/Jenny and future channels still need to call the same system.

## Channel Model

The Advisory Board is channel-agnostic.

Telegram is only the first practical communication channel. The same advisor core should later support other channels such as Discord, Slack, WhatsApp, email, web chat, desktop, API calls, or Jenny/OpenClaw internal calls.

Channel-specific adapters may handle routing, identity mapping, permissions, formatting, and loop guards. They must not own the advisor personality, memory policy, source policy, or board logic.

### Naming Rule

The public display names should be the real public names, not role labels.

Use:

- Steve Jobs
- Warren Buffett
- Elon Musk
- Alex Hormozi
- Peter Thiel
- Jeff Bezos

Do not append `Advisor`, `Bot`, or `Advisor Bot` to visible names. `Advisor` is the role/position inside the system, not part of the public identity name.

## Advisor Stability And Development Policy

Advisors must not evolve themselves.

Hard rules:

- Advisors must not create, edit, or install skills.
- Advisors must not rewrite their own prompts.
- Advisors must not change their own memory policy or source policy.
- Advisors must not autonomously add long-term behavioral rules.
- Advisors must not run self-development loops.
- Advisors must not become workers or autonomous operators.

Allowed development path:

- Advisor improvement happens only from outside the advisor runtime.
- Andras or an authorized maintainer can update advisor profiles.
- New public materials, publications, interviews, books, shareholder letters, podcasts, and transcripts can be processed into source notes.
- Source notes can update an advisor's knowledge and examples, but not randomly mutate the advisor's core role.
- Every durable personality or knowledge update should be explicit, reviewable, and versionable.

Practical meaning:

- An advisor can answer a question.
- An advisor can suggest that its profile might need improvement.
- An advisor cannot apply that improvement by itself.
- A separate maintainer workflow may later ingest sources and propose profile updates for review.

## Clean Operating Model

```txt
Andras
  |
Channels
  |- direct advisor chats
  |- Advisory Board room where supported
  |- Jenny / OpenClaw front door
  |
Jenny / OpenClaw
  |- quick board calls
  |- personal context
  |- final summaries
  |
Hermes identity/profile layer
  |- Steve Jobs
  |- Warren Buffett
  |- Elon Musk
  |- Alex Hormozi
  |- Peter Thiel
  |- Jeff Bezos
  |- Moderator
  |
Marveen worker agents for execution
```

Hermes is the advisor presence layer. OpenClaw/Jenny is the personal assistant and summary layer. Marveen is the worker team.

## Model Architecture

Recommended model split:

- GPT: advisor persona engine
- GPT: default board moderator when available through the chosen Hermes/OpenClaw adapter path
- Claude Opus: optional challenge-mode moderator or second-opinion model
- Gemini: research engine for long materials
- NotebookLM: optional research workbench, not runtime brain

### GPT Advisor Personas And Moderator

GPT should run the individual advisor lenses because the key requirement is stable persona shaping and consistent instruction-following.

If Hermes can route the advisor profiles to GPT-5.5 through the desired authentication path, the board moderator should also use GPT-5.5 by default. If Hermes cannot use that model path directly, model routing should be kept behind the advisor core adapter so OpenClaw/Codex can still serve GPT-backed calls where needed.

Each advisor is not a celebrity impersonation. Each one is a decision framework inspired by publicly known thinking patterns.

Examples:

- Musk-lens: first principles, 10x ambition, engineering execution
- Jobs-lens: taste, focus, product magic, simplicity
- Buffett-lens: capital discipline, risk, long-term compounding
- Hormozi-lens: offer, sales, pricing, revenue machine
- Thiel-lens: moat, monopoly, category strategy
- Bezos-lens: customer obsession, operating system, marketplace execution

### Board Moderator

The moderator should not be hardcoded to Claude Opus.

Default target:

- use GPT-5.5 when available through the chosen Hermes/OpenClaw adapter path

Optional:

- use Claude Opus for challenge mode, deep strategic counterargument, or a second verdict

Responsibilities:

- decide which advisors to call
- keep advisor answers short and distinct
- identify disagreements
- force tradeoffs
- produce the final verdict
- return risks and next actions

### Gemini Research Engine

Gemini should process new long-form source material:

- YouTube transcripts
- podcasts
- interviews
- books and excerpts
- shareholder letters
- long articles
- market research
- competitor pages

Gemini's output should not directly become final advice. It should be converted into source notes, tagged, stored, and then retrieved by the advisor board when needed.

### NotebookLM Role

NotebookLM can be used as a research workbench:

- collect sources around one advisor or topic
- build a source-grounded understanding of a body of material
- generate summaries or briefing notes
- compare multiple documents

NotebookLM should not be the main runtime because Jenny needs direct, scriptable, auditable access to the board.

## Advisor Team

### Core 5

1. Elon Musk, 10x vision and first-principles execution
2. Steve Jobs, product taste and focus
3. Warren Buffett, capital discipline and long-term judgment
4. Alex Hormozi, offer design, sales, pricing, and monetization
5. Peter Thiel, moat, monopoly, and category strategy

This is the recommended default board.

### Strong Sixth Seat

Jeff Bezos is the strongest challenger to Peter Thiel.

Bezos is especially strong when the question is:

- marketplace execution
- customer experience
- operations
- repeat usage
- trust systems
- logistics or supply-demand engines
- building a machine that compounds over 10 years

Thiel is stronger when the question is:

- defensibility
- monopoly seed
- category creation
- contrarian strategy
- platform positioning
- whether an idea is only a feature or a real strategic wedge

Current recommendation:

- Keep Thiel in the default core board.
- Add Bezos as a selectable challenger.
- For topescortbabes.com or marketplace-heavy decisions, call Bezos.
- For OpenClaw, Secret Project, and category-level strategy, call Thiel.

### Extended Board

Useful optional advisors:

- Naval Ravikant: leverage, internet scale, personal freedom
- Charlie Munger: mental models and decision hygiene
- Richard Branson: brand, PR, partnership boldness
- Rory Sutherland: psychology, framing, irrational customer behavior
- Sam Altman: AI platform strategy and startup execution
- Paul Graham: founder clarity, simple products, fast iteration
- Ben Horowitz: company building and hard leadership decisions
- Marc Andreessen: tech trends, venture logic, platform shifts
- Jensen Huang: AI infrastructure and long-term technical positioning

Brian Tracy belongs in the training library, not the core board. He can be useful for sales discipline, goal setting, and productivity, but he is not sharp enough for AI, platform, moat, or 10x strategy decisions.

## Runtime Flow

Default Jenny flow:

1. Andras asks Jenny a strategic question from any supported channel.
2. Jenny decides whether the board is needed.
3. Jenny calls `askBoard()` with the question, context, and optional advisors.
4. The moderator selects the required advisors.
5. Each advisor returns a short, opinionated perspective.
6. The moderator compares the answers.
7. Jenny returns the final answer to Andras in a concise channel-native format.

Direct advisor flow:

1. Andras opens a direct chat or route to one named advisor.
2. The channel adapter resolves the public identity to the canonical advisor ID.
3. The advisor answers using its stable profile and approved source context.
4. The advisor does not alter itself, create skills, or persist new personality rules.

Direct command flow:

- `/board <question>` calls the default board
- `/advisor musk <question>` calls one advisor
- `/debate <decision>` forces disagreement and tradeoff analysis
- `/verdict <situation>` returns only the final decision, risk, and next step
- `/research <source>` ingests or summarizes source material for later review
- `/delegate <task>` sends execution work to a Marveen worker agent

## Response Format

Default board response:

```md
## Advisor Views

Musk:
<10x / first-principles view>

Jobs:
<product and taste view>

Buffett:
<capital and risk view>

Hormozi:
<offer and monetization view>

Thiel or Bezos:
<moat or operating engine view>

## Moderator Verdict

Decision:
<clear recommendation>

Why:
<short reasoning>

Main risk:
<biggest risk>

Next step:
<one concrete action>
```

Channel-facing responses should usually be shorter than the full internal board output.

## Proposed Project Structure

```txt
advisory-board/
  README.md
  advisors/
    jobs.md
    buffett.md
    hormozi.md
    musk.md
    thiel.md
    bezos.md
  prompts/
    moderator.md
    advisor-template.md
  memory/
    jobs.sqlite
    buffett.sqlite
    hormozi.sqlite
    musk.sqlite
    thiel.sqlite
    bezos.sqlite
    shared.sqlite
  sources/
    raw/
    processed/
  openclaw-adapter/
    askAdvisor.ts
    askBoard.ts
    delegateMarveenWorker.ts
  hermes-adapter/
    profiles/
    channels/
      telegram.md
      routing.md
      privacy-and-loop-guards.md
  scripts/
    ingest_source.ts
    build_index.ts
  docs/
    decisions.md
    runtime-comparison.md
    channel-advisory-board-ux.md
    source-policy.md
```

## Advisor Profile Format

Each advisor profile should contain:

- role
- what this advisor optimizes for
- what this advisor ignores or underweights
- core questions
- decision filters
- source references
- output style
- prohibited behavior
- self-development restrictions

Example:

```md
# Musk Lens

Role: first-principles, 10x execution, engineering courage.

Optimizes for:
- speed
- scale
- technical leverage
- vertical integration
- impossible goals made concrete

Core questions:
- What would this look like if it had to be 10x bigger?
- Which assumption is fake?
- What can be reduced to physics, software, or direct execution?

Avoid:
- celebrity imitation
- personal gossip
- theatrical tone
- generic motivation
- self-improvement or skill creation
- autonomous task execution
```

## Knowledge System

Use two layers:

1. Structured advisor profiles
2. Source-backed knowledge base

The structured profiles define how the advisor thinks.

The knowledge base stores source material:

- raw text
- summary
- key ideas
- advisor tags
- topic tags
- source URL
- date
- confidence

Recommended storage:

- per-advisor SQLite files for advisor-specific source memory
- shared SQLite for cross-advisor topics and board-level decisions
- vector index for retrieval
- plain markdown for human-readable advisor profiles

## Source Ingestion

Source ingestion should produce clean, reusable notes.

Input examples:

- podcast transcript
- YouTube transcript
- book excerpt
- interview
- shareholder letter
- article

Output format:

```md
# Source Note

Title:
Author / speaker:
Date:
URL:
Advisor tags:
Topic tags:

## Summary

## Key Ideas

## Quotes

## How This Updates The Advisor Lens

## Retrieval Notes
```

Important rules:

- New source material can update an advisor's knowledge and examples.
- New source material must not randomly change an advisor's core role.
- Advisor updates must be applied by an external maintainer workflow, not by the advisor itself.
- The board must stay stable and reviewable.

## Jenny, Hermes, And Channel Integration

Hermes should expose each advisor as a direct identity across supported channels and expose a formal Advisory Board room where a channel supports it. Jenny should get callable adapter functions, but the board should remain usable without Jenny.

```ts
askAdvisor({
  advisor: "jobs" | "buffett" | "hormozi" | "musk" | "thiel" | "bezos",
  question: string,
  context?: string,
  mode?: "quick" | "research_grounded"
})

askBoard({
  question: string,
  context?: string,
  advisors?: string[],
  mode?: "quick" | "debate" | "verdict" | "research_grounded",
  project?: "openclaw" | "secret-project" | "topescortbabes" | "presence-lab" | "general"
})

delegateMarveenWorker({
  task: string,
  workerType: "research" | "development" | "sales" | "content" | "ops",
  context?: string
})
```

Modes:

- `quick`: short answer from 2 or 3 relevant advisors
- `debate`: advisors disagree and expose tradeoffs
- `verdict`: only final decision, risk, and next step
- `research_grounded`: retrieve source notes before answering

Rules:

- advisor calls are for thinking
- Marveen delegation is for execution
- advisor runtime must not create skills or self-modify
- source ingestion is a separate maintainer workflow

## MVP

The MVP should be small and useful.

### Phase 1, Direct Advisor Chats

- Create advisor markdown profiles.
- Create CLI command: `ask-advisor jobs "<question>"`.
- Create Hermes profiles for each advisor.
- Map each advisor profile to individual direct-chat identities using the plain public name.
- Support at least one real channel first, but keep the adapter model channel-agnostic.
- Support direct private chats first so Andras can tune each personality one by one.
- Return short, opinionated, channel-native answers.
- Enforce no self-development and no skill creation.

### Phase 2, Static Board

- Create moderator prompt.
- Create CLI command: `ask-board "<question>"`.
- Return structured markdown output.

### Phase 3, Board Room

- Add board-room routing and loop guards for channels that support group discussion.
- Support formal board sessions.

### Phase 4, Jenny Tool

- Add OpenClaw adapter around `askBoard()` and `askAdvisor()`.
- Allow Jenny to call the board and summarize the result.
- Add `/board`, `/advisor`, `/debate`, and `/verdict` commands where useful.

### Phase 5, Knowledge Base

- Add SQLite metadata store.
- Add source ingestion script.
- Add vector retrieval.
- Add source-grounded answers.

### Phase 6, Research Workflow

- Use Gemini to process long sources.
- Optionally use NotebookLM as manual workbench.
- Store extracted source notes in `sources/processed/`.
- Propose advisor profile updates externally for review.

## Success Criteria

The system is successful if:

- Jenny can call the board without manual setup.
- Andras can ask a strategic question from at least one supported channel.
- Andras can call individual advisors directly without going through Jenny's personality layer.
- Each core advisor can exist as a distinct identity across supported channels.
- A private Advisory Board room can run moderated sessions without advisor loops where the channel supports it.
- The advisors give distinct perspectives, not generic business advice.
- The final verdict is short, clear, and actionable.
- The board can cite internal source notes when research-grounded mode is used.
- Advisor behavior remains stable over time.
- Advisors do not self-modify, self-improve, or create skills.
- Marveen is used only when execution is needed.

## Open Decisions

- Final fifth core seat: Thiel by default, Bezos as challenger.
- Exact model names should be configured at runtime because availability and pricing change.
- Confirm the exact model path Hermes should use for advisor profiles.
- Confirm how OpenClaw/Jenny should call Hermes board sessions and receive summaries.
- Decide which channel ships first.
- Decide whether advisor output should be cached per question.
- Decide whether source ingestion should run manually, on schedule, or from a command.
- Decide whether NotebookLM should be used only manually or also through an enterprise API later.

## Next Build Step

Create the first working Hermes-oriented MVP:

```txt
Hermes profiles:
  jobs
  buffett
  hormozi
  musk
  thiel
  bezos
  moderator

Channels:
  direct private chat per advisor
  optional private Advisory Board room where supported
```

Expected first milestone:

- no database yet
- no vector search yet
- only markdown profiles, Hermes profile wrappers, moderator prompt, channel routing, and loop guards
- direct advisor chat works on the first chosen channel
- no advisor can create skills or self-modify
- one moderated board session works later
- callable locally by Jenny
