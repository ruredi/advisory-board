# Direct Advisor Chat

Created: 2026-06-30  
Project: Advisory Board

## Status

Local direct advisor chat is available through the `scripts/ask_advisor.py` runner.

This is the first test surface for tuning individual advisor personalities before board mode.

## Important: Hermes Chat vs Terminal Script

Do **not** type `/jobs` directly into Hermes chat. Hermes treats leading `/...` text as a native slash command, and `/jobs` is not a registered Hermes command.

Use chat-safe routing text instead:

```txt
jobs: What should we cut?
buffett: Is this business durable?
jobs,buffett: Should we build board mode now?
```

If you send one of those chat-safe lines to the main Hermes chat, the main agent/router can call the local advisor runner for you.

Leading-slash forms like `/jobs ...` are only safe when passed as a quoted argument to the terminal script:

```bash
python3 scripts/advisor.py "/jobs What should we cut?"
```

## Available Advisors

```bash
python3 scripts/ask_advisor.py --list
```

Current advisor IDs:

- `jobs` — Steve Jobs
- `buffett` — Warren Buffett
- `musk` — Elon Musk
- `hormozi` — Alex Hormozi
- `thiel` — Peter Thiel
- `bezos` — Jeff Bezos

## Convenient Routing Commands

Preferred chat-safe syntax:

```bash
python3 scripts/advisor.py "jobs: What should we cut from this product?"
python3 scripts/advisor.py "buffett: Is this business durable?"
python3 scripts/advisor.py "musk: What is the 10x version of this?"
python3 scripts/advisor.py "hormozi: How would you package this offer?"
python3 scripts/advisor.py "thiel: What is the monopoly wedge here?"
python3 scripts/advisor.py "bezos: What operating mechanism would make this compound?"
```

Ask multiple advisors with one command:

```bash
python3 scripts/advisor.py "jobs,buffett: Should we build board mode now?"
python3 scripts/advisor.py "musk+thiel: What is the 10x monopoly wedge?"
```

Full public-name slug aliases also work:

```bash
python3 scripts/advisor.py "steve-jobs: What should we cut from this product?"
python3 scripts/advisor.py "warren-buffett: Is this business durable?"
python3 scripts/advisor.py "elon-musk: What is the 10x version of this?"
```

Terminal-only slash syntax also works when quoted as a script argument:

```bash
python3 scripts/advisor.py "/jobs What should we cut from this product?"
python3 scripts/advisor.py "/steve-jobs What should we cut from this product?"
```

List routes:

```bash
python3 scripts/advisor.py --list
```

## Lower-Level Ask One Advisor

The lower-level runner is still available:

```bash
python3 scripts/ask_advisor.py jobs "Should we build individual advisor chats before board mode?"
```

## Dry Run

Use dry-run to inspect the exact prompt without calling Hermes:

```bash
python3 scripts/advisor.py "jobs: Should we ship it?" --dry-run
python3 scripts/ask_advisor.py jobs "Should we ship it?" --dry-run
```

## Governance

Every advisor runner call injects the stability rules:

- no skill creation
- no skill editing/installing
- no prompt self-rewrite
- no memory/source-policy self-change
- no autonomous self-development loop
- no worker-agent execution

If an advisor notices a weakness in its own profile, it may mention it as feedback for an external maintainer. It must not apply that change itself.
