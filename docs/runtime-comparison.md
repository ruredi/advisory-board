# Runtime Comparison: OpenClaw vs Hermes

Created: 2026-06-29  
Project: Advisory Board

## Question

Which runtime is better for the Advisory Board: OpenClaw or Hermes?

The important requirement is not worker execution. The advisors are thinking lenses. The real question is which system gives the best combination of:

- stable separate advisor identities
- direct advisor chat
- Jenny integration
- board moderation
- multi-channel access
- source-backed memory
- strict no-self-development governance
- low operational complexity

## What We Want

The target system:

```txt
Andras
  |
Channels
  |- direct chat with Steve Jobs / Warren Buffett / Elon Musk / ...
  |- board room where the channel supports group discussion
  |- Jenny / OpenClaw front door
  |
Jenny / OpenClaw
  |- /advisor jobs ...
  |- /advisor buffett ...
  |- /board ...
  |- /delegate marveen-worker ...
  |
Marveen worker agents
```

Advisors think. Marveen workers execute.

The advisors should not be baked into Jenny. Jenny should be able to call them, but Andras should also be able to speak with them directly.

Telegram is only one possible channel. The runtime choice must not assume that Telegram is the product. The product is the Advisory Board and its separate advisor identities.

## Non-Negotiable Advisor Governance

Advisors must remain stable lenses.

They must not:

- create skills
- edit skills
- install skills
- rewrite their own prompts
- change their own memory policy
- run self-development loops
- become autonomous worker agents

Advisor development happens externally, through reviewed updates to advisor profiles and source notes. New public materials can improve the advisors, but only via a maintainer workflow outside the advisor runtime.

## OpenClaw Strengths

OpenClaw is strongest when the Advisory Board is mainly a tool that Jenny and Andras can call.

Strengths:

- Jenny is already the main interface.
- Local memory, files, scripts, and project routing are already available.
- Easy to add `askAdvisor()` and `askBoard()` as tools.
- Easier to keep one canonical project directory and one source of truth.
- Easier to integrate with Codex, Gemini, local scripts, SQLite, and future source ingestion.
- Better for fast MVP.
- Better when the board is a strategic function inside the existing personal AI operating system.

Weaknesses:

- Separate advisor identities must be implemented manually.
- Separate direct-chat channels per advisor require custom routing.
- Direct chat with "Steve Jobs" or "Warren Buffett" may feel like a command mode, not like a separate advisor entity, unless we build extra UX.
- State isolation depends on our implementation discipline.

Best fit:

- Jenny asks the board.
- Andras uses `/board` and `/advisor`.
- Advisor output is primarily a structured decision aid.
- We want fast, versionable, local implementation.

## Hermes Strengths

Hermes is strongest when the advisors should feel like clearly separated named entities.

Useful Hermes patterns:

- Profiles: named agents with separate config, memory, and state.
- Messaging gateway: multiple communication surfaces can point to agent identities.
- Delegation: useful for implementation and research helpers, but not for the advisors themselves.
- Clear separation between advisor identities and worker agents.

Strengths for Advisory Board:

- Cleaner separation of advisor personalities.
- More natural mapping to one profile per advisor.
- Easier to map advisor profiles to channel-specific identities.
- Direct "talk to Steve Jobs" or "talk to Warren Buffett" experience can feel more native.
- Better if Andras wants advisor identities to be first-class chat participants.
- Can be independent from OpenClaw if needed.

Weaknesses:

- More runtime complexity.
- Hermes can be powerful enough to tempt the advisors into worker-like behavior, which must be explicitly forbidden.
- Kanban and task handoff are mostly unnecessary for pure advisory thinking.
- Need an adapter back into Jenny/OpenClaw.
- Model routing may be less direct if the preferred GPT-5.5 access is through OpenClaw OAuth.
- Higher risk that advisors accumulate too much lifecycle and state unless governance is strict.

Best fit:

- Each advisor should have a distinct profile and direct-chat identity.
- Andras wants to chat with advisors directly as named participants.
- Advisor separation is more important than MVP speed.
- Hermes already provides enough profile/channel infrastructure to avoid custom building it.

## Key Tradeoff

OpenClaw gives us better Jenny integration.

Hermes gives us better separated advisor presence.

That is the whole decision.

If the Advisory Board is mainly "Jenny, ask the board", choose OpenClaw first.

If the Advisory Board is mainly "I want to talk to Steve Jobs, Warren Buffett, Elon Musk, and the board as separate entities", Hermes becomes stronger.

## Recommended Architecture

Do not hardcode the advisor system into either runtime.

Build a runtime-agnostic advisor core:

```txt
advisory-board/
  advisors/
    jobs.md
    buffett.md
    hormozi.md
    musk.md
    thiel.md
    bezos.md
  prompts/
    moderator.md
  memory/
    jobs.sqlite
    buffett.sqlite
    hormozi.sqlite
    musk.sqlite
    thiel.sqlite
    bezos.sqlite
    shared.sqlite
  openclaw-adapter/
    askAdvisor.ts
    askBoard.ts
  hermes-adapter/
    profiles/
    channels/
      routing.md
      telegram.md
```

This keeps the strategic content portable.

OpenClaw can call the same advisor core.

Hermes can host the same advisor core as separate profiles if we decide that direct separated identities are important.

Channel adapters can expose those identities on Telegram or any later channel, but the advisor core must not depend on one channel.

## Practical Decision

Recommended now:

1. Keep the advisor core as a standalone project.
2. Make direct advisor chat the first MVP so Andras can tune each personality one by one.
3. Keep the interface channel-agnostic; Telegram can be the first channel but not the architecture.
4. Use Hermes profiles early if separated direct identities are the desired product experience.
5. Keep OpenClaw/Jenny as the central personal assistant and summary interface either way.
6. Enforce no skill creation, no self-modification, and no autonomous self-development for advisor profiles.

This avoids premature runtime and channel lock-in.

## Verdict

For a command-based MVP, OpenClaw is still the better default because it gets Jenny and Andras using the board fastest.

But Hermes has the strongest argument for one specific requirement:

Separate advisor identities with separate direct chat channels.

If that requirement is emotionally and practically important, Hermes should become the first interface layer.

So the final decision should not be "OpenClaw or Hermes" at the core level.

The stronger decision is:

- advisor core is runtime-agnostic
- channel adapters are runtime-specific and replaceable
- Hermes adapter is the first interface if separate advisor identities are the desired product experience
- OpenClaw adapter remains required so Jenny can call the board and return summaries
- Marveen remains the worker layer for execution tasks
- advisor profiles remain stable and do not self-improve

Detailed channel UX plan: `docs/channel-advisory-board-ux.md`

## Decision Trigger

Move advisor runtime toward Hermes if any of these become must-have requirements:

- each advisor needs its own direct chat identity
- advisor identities need independent state beyond simple SQLite memory
- Andras wants to spend meaningful time directly chatting with one advisor at a time
- Hermes profiles already provide the separation faster than custom OpenClaw routing
- more than one communication channel will eventually expose the same advisor identities

Current user preference:

- separate direct advisor identities are strongly preferred
- visible names should be the real public names, not `Advisor` or `Bot` labels
- Telegram is only one channel, not the product boundary
- an Advisory Board room with Jenny and all advisors is desirable where the channel supports it
- Jenny may orchestrate quick calls, but a separate Moderator profile is useful for formal board sessions
- advisors must not create skills or self-develop; improvements come only from external source/profile updates

Stay OpenClaw-first if the main usage is:

- ask Jenny
- call `/board`
- call `/advisor`
- get a structured strategic verdict
- keep implementation small and inspectable
