# Channel-Agnostic Advisory Board UX

Created: 2026-06-29  
Project: Advisory Board

## Core Insight

The Advisory Board should not only be a command system.

The stronger product experience is that Andras can have multiple distinct advisors available as named identities across communication channels:

- Jenny
- Elon Musk
- Steve Jobs
- Warren Buffett
- Alex Hormozi
- Peter Thiel
- Jeff Bezos
- optional Moderator

Telegram is only one channel where these identities can appear. The product is the Advisory Board, not Telegram.

This changes the runtime preference.

If separate advisor identities and a shared board room are important, Hermes becomes the stronger interface layer because it maps more naturally to separate profiles, separate state, and separate chat identities. Channel-specific routing should stay in adapters.

## Target Experience

### Channel Naming Rule

The channel-facing names should be the plain public names, not role labels.

Use:

- Steve Jobs
- Warren Buffett
- Elon Musk
- Alex Hormozi
- Peter Thiel
- Jeff Bezos

Do not use names like `Jobs Advisor`, `Buffett Bot`, or `Musk Advisor Bot`. `Advisor` is their position in the system, not part of the displayed identity.

### Direct Advisor Chat

Andras can message one advisor directly through any supported channel:

```txt
Andras -> Steve Jobs
Andras -> Warren Buffett
Andras -> Elon Musk
```

Each advisor keeps its own style, approved source context, and stable profile.

The first build should prioritize direct advisor chat so Andras can tune the personalities one by one before formal board sessions exist.

### Advisory Board Room

Where a channel supports multi-party discussion, create a private group/room/thread for board discussion:

```txt
Advisory Board room
  Andras
  Jenny
  Moderator
  Elon Musk
  Steve Jobs
  Warren Buffett
  Alex Hormozi
  Peter Thiel
  Jeff Bezos
```

Telegram is one possible implementation using a private group or supergroup. Other channels may map this to a Slack channel, Discord private channel, web room, email thread, or internal Jenny/OpenClaw session.

### Jenny-As-Front-Door Mode

Andras can still ask Jenny normally:

```txt
Andras -> Jenny
Jenny -> Board / Moderator
Board discusses internally or in a room
Jenny -> Andras with final answer only
```

This keeps the main daily UX clean while still allowing deep board debate behind the scenes.

### Board-Visible Mode

Andras can ask inside the Advisory Board room:

```txt
Andras -> Advisory Board room
Moderator assigns turns
Advisors answer briefly
Moderator returns verdict
Jenny can add personal context
```

## Advisor Stability And Development Policy

The advisors must not evolve themselves.

Hard rules:

- Advisors do not create skills.
- Advisors do not edit or install skills.
- Advisors do not rewrite their own profiles or prompts.
- Advisors do not add permanent rules to themselves.
- Advisors do not change their own memory/source policy.
- Advisors do not start autonomous self-improvement loops.
- Advisors do not execute worker tasks.

Allowed development path:

- Development happens externally through profile/source updates.
- Andras or an authorized maintainer can update the advisor markdown profiles.
- New public source material can be processed into source notes.
- Source notes can update knowledge, examples, and retrieval context.
- Core personality changes should be explicit, reviewed, and versionable.

Advisor behavior during chat:

- An advisor may say, "This reveals a weakness in my lens/profile."
- An advisor may suggest what should be improved.
- The advisor must not apply that improvement itself.
- A separate maintainer/research workflow can later decide whether to update the profile.

## Orchestrator Choice

There are two valid modes.

### Jenny As Orchestrator

Best for:

- quick decisions
- personal context
- short answers
- when Andras wants one final answer

Pros:

- simplest UX
- Jenny already knows Andras
- no extra moderator identity needed

Cons:

- Jenny may blend personal assistant judgment with board moderation
- less "independent board" feeling

### Separate Moderator

Best for:

- formal board sessions
- visible multi-advisor debate
- turn-taking
- less bias from Jenny

Pros:

- clearer process
- prevents advisor chatter
- can enforce answer length and role discipline
- makes the board feel like a real advisory room

Cons:

- one more profile/identity
- slightly more complexity

Recommendation:

- use Jenny as quick orchestrator
- add a separate `moderator` profile for formal board sessions

## Runtime Implication

Updated recommendation:

- advisor core remains runtime-agnostic
- channel adapters remain replaceable
- Hermes becomes the preferred interface layer for separate advisor identities and board rooms
- OpenClaw remains Jenny's operating layer and can call the board
- Marveen remains worker execution layer
- advisors remain stable lenses, not self-improving agents

## Proposed Structure

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
  hermes-adapter/
    profiles/
      jobs.profile.md
      buffett.profile.md
      hormozi.profile.md
      musk.profile.md
      thiel.profile.md
      bezos.profile.md
      moderator.profile.md
    channels/
      routing.md
      telegram.md
      privacy-and-loop-guards.md
  openclaw-adapter/
    askAdvisor.ts
    askBoard.ts
    summarizeBoardVerdict.ts
```

## Loop Guards

Multiple channel-facing identities in one room can accidentally trigger each other. The board needs strict routing rules.

Rules:

- advisors respond only when called by the moderator, Jenny, or Andras
- advisors do not respond to other advisor messages unless explicitly asked
- the moderator owns turn-taking in board mode
- each board session has a session ID
- each advisor gives one answer per round
- Jenny summarizes only when asked or when the moderator marks the session final
- channel adapters suppress accidental cross-triggering
- advisors never turn routing events into durable self-updates

## Identity Requirements

Each advisor identity should have:

- distinct display name using the plain public name
- distinct avatar where the channel supports it
- own profile prompt
- own approved source context
- own constrained memory/state if needed
- same shared source system
- clear disclaimer in system behavior: decision framework, not celebrity impersonation
- explicit prohibition on self-development and skill creation

## Updated Verdict

If the goal is only "Jenny can ask a board", OpenClaw-first is enough.

If the goal is "I want multiple advisors as separate direct-chat presences", Hermes should be the first interface layer.

Given Andras's preference for separate advisor identities, the recommended direction is now:

1. Build runtime-agnostic advisor core.
2. Design Hermes profile and channel mapping early.
3. Prioritize direct one-on-one advisor chats first.
4. Keep OpenClaw/Jenny as the central personal assistant and summary interface.
5. Use a separate Moderator profile for formal board sessions.
6. Let Jenny orchestrate only quick/private board calls.
7. Keep advisor development external, source-backed, and reviewable.
