# Telegram Direct Advisors

Created: 2026-06-30  
Project: Advisory Board

## Goal

Andras should be able to talk to each advisor separately on Telegram:

- Steve Jobs
- Warren Buffett
- Elon Musk
- Alex Hormozi
- Peter Thiel
- Jeff Bezos

Telegram is only the first channel. The core advisor profiles stay channel-agnostic.

## Architecture

Use one Hermes profile and one Telegram bot token per advisor:

```txt
Telegram DM: Steve Jobs      -> Hermes profile: jobs
Telegram DM: Warren Buffett  -> Hermes profile: buffett
Telegram DM: Elon Musk       -> Hermes profile: musk
Telegram DM: Alex Hormozi    -> Hermes profile: hormozi
Telegram DM: Peter Thiel     -> Hermes profile: thiel
Telegram DM: Jeff Bezos      -> Hermes profile: bezos
```

Each advisor profile should have:

- model: `gpt-5.5`
- provider: `openai-codex`
- reasoning/thinking: `high`
- toolset: `safe`
- no bundled skills
- no self-development
- its own Telegram bot token
- Andras's Telegram user ID in `TELEGRAM_ALLOWED_USERS`

## BotFather Setup

Create six bots with @BotFather.

Display names should be the plain public names:

| Advisor | Bot display name | Username requirement |
|---|---|---|
| jobs | Steve Jobs | must end in `bot` |
| buffett | Warren Buffett | must end in `bot` |
| musk | Elon Musk | must end in `bot` |
| hormozi | Alex Hormozi | must end in `bot` |
| thiel | Peter Thiel | must end in `bot` |
| bezos | Jeff Bezos | must end in `bot` |

Telegram usernames must be globally unique and end in `bot`, so examples like `andras_steve_jobs_bot` may be needed.

For each bot:

1. Message @BotFather.
2. Send `/newbot`.
3. Set display name to the public name.
4. Choose a unique username ending in `bot`.
5. Copy the API token.
6. Optionally set avatar with `/setuserpic`.
7. Optionally set description/about text.

## Required Secrets

Each profile needs its own `.env` file:

```txt
~/.hermes/profiles/jobs/.env
~/.hermes/profiles/buffett/.env
~/.hermes/profiles/musk/.env
~/.hermes/profiles/hormozi/.env
~/.hermes/profiles/thiel/.env
~/.hermes/profiles/bezos/.env
```

Template per profile:

```bash
TELEGRAM_BOT_TOKEN=<token from BotFather>
TELEGRAM_ALLOWED_USERS=<Andras numeric Telegram user ID>
```

Get the numeric Telegram user ID by messaging @userinfobot or @get_id_bot.

Do not use Telegram usernames for `TELEGRAM_ALLOWED_USERS`; Hermes expects numeric IDs.

## Start Gateways

After each `.env` has the correct token and allowed user ID:

```bash
hermes --profile jobs gateway start
hermes --profile buffett gateway start
hermes --profile musk gateway start
hermes --profile hormozi gateway start
hermes --profile thiel gateway start
hermes --profile bezos gateway start
```

Check status:

```bash
hermes gateway list
```

Stop one profile:

```bash
hermes --profile jobs gateway stop
```

Restart after config changes:

```bash
hermes --profile jobs gateway restart
```

## Current Local Preparation

The Hermes profiles have been created:

- `jobs`
- `buffett`
- `musk`
- `hormozi`
- `thiel`
- `bezos`

They have been configured for:

- `model.default = gpt-5.5`
- `model.provider = openai-codex`
- `agent.reasoning_effort = high`
- `toolsets = ["safe"]`
- no bundled skills

The remaining required step is adding each Telegram token and Andras's numeric Telegram user ID to the profile `.env` files.

## Advisor Identity Prompt

Each profile needs its `SOUL.md` rendered from two reviewed sources:

```txt
advisors/persona_config.json  -> structured persona, behavior rules, voice bible
advisors/jobs.md              -> durable advisor lens/source policy/governance
advisors/buffett.md           -> durable advisor lens/source policy/governance
...
```

Render a reviewed SOUL file with:

```bash
python3 scripts/render_profile_soul.py jobs > /tmp/jobs-SOUL.md
```

Then copy the reviewed content into the matching profile `SOUL.md`.

The generated SOUL is layered:

1. Global safety/product rules
2. Stable governance
3. Structured persona config
4. Concrete behavior rules
5. Voice bible (`sounds like` / `does not sound like`)
6. Failure modes
7. Response assembly rules
8. Durable advisor lens

The SOUL prompt must include:

- not the real person
- stable advisory lens
- no skill creation
- no self-prompt rewrite
- no memory/source-policy self-change
- no self-development
- no worker-agent execution
- concise Telegram-native answers

If Hermes blocks automated cross-profile writes, apply these SOUL files manually or approve the write operation in the Hermes UI.
