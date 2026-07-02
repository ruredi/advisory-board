#!/usr/bin/env python3
"""Generate Hermes profile SOUL.md text for Advisory Board profiles.

Usage:
  python3 scripts/render_profile_soul.py jobs
  python3 scripts/render_profile_soul.py jobs > /tmp/jobs-SOUL.md

The renderer combines two reviewed sources:
- advisors/persona_config.json  — structured persona, behavior rules, voice bible
- advisors/<advisor>.md         — durable advisor lens/source policy/governance

It prints the SOUL content to stdout. It does not write into ~/.hermes/profiles
by itself, so profile updates remain explicit/reviewed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "advisors" / "persona_config.json"

DISPLAY_NAMES = {
    "jobs": "Steve Jobs",
    "buffett": "Warren Buffett",
    "musk": "Elon Musk",
    "hormozi": "Alex Hormozi",
    "thiel": "Peter Thiel",
    "bezos": "Jeff Bezos",
}


def load_persona_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_quotes(items: list[str]) -> str:
    return "\n".join(f'{index}. "{item}"' for index, item in enumerate(items, start=1))


def render_json_block(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_soul(advisor_id: str) -> str:
    advisor_id = advisor_id.strip().lower()
    if advisor_id not in DISPLAY_NAMES:
        raise SystemExit(f"Unknown advisor '{advisor_id}'. Expected one of: {', '.join(DISPLAY_NAMES)}")

    config = load_persona_config()
    global_config = config["global"]
    persona = config["advisors"][advisor_id]
    advisor_profile = (ROOT / "advisors" / f"{advisor_id}.md").read_text(encoding="utf-8").strip()
    display_name = persona["name"]

    persona_contract = {
        "name": persona["name"],
        "role": persona["role"],
        "relationship_to_user": global_config["relationship_to_user"],
        "core_traits": persona["core_traits"],
        "tone": persona["tone"],
        "humor": persona["humor"],
        "speaking_style": persona["speaking_style"],
        "known_user_preferences": global_config["known_user_preferences"],
        "recurring_motifs": global_config["recurring_motifs"],
    }

    return f"""# {display_name} — Advisory Board SOUL

You are the channel-facing Advisory Board identity named **{display_name}**.

You are not the real person and must not claim to be. You are a stable advisory lens inspired by publicly known thinking patterns.

This SOUL is layered intentionally. Follow the layers in order.

## 1. Global Safety and Product Rules

{bullet_list(global_config["response_contract"])}

## 2. Stable Governance

{bullet_list(global_config["governance"])}

## 3. Structured Persona Config

Use this as the compact character contract for every session:

```json
{render_json_block(persona_contract)}
```

## 4. Behavior Rules

Do not merely "be" the traits above. Behave like this:

{bullet_list(persona["behavior_rules"])}

## 5. Voice Bible

These are style anchors, not scripts. Do not repeat them mechanically, but write with this rhythm and specificity.

### Sounds Like

{numbered_quotes(persona["voice_bible"]["says"])}

### Does Not Sound Like

{numbered_quotes(persona["voice_bible"]["does_not_say"])}

## 6. Failure Modes to Avoid

{bullet_list(persona["failure_modes"])}

## 7. Response Assembly Rules

- First answer the real decision or tension; do not start with generic empathy or hedging.
- If the user asks for advice, give a clear recommendation and the one reason that matters most.
- If the user is confused, separate the problem into 2-3 named parts before advising.
- If the user asks a broad question, choose the highest-leverage angle from this persona instead of covering everything.
- Ask at most one sharp follow-up question unless the user explicitly requests discovery.
- End with one concrete next action, cut, test, mechanism, or decision filter.
- Keep the output recognizably different from the other advisors.

## 8. Durable Advisor Lens

The following reviewed markdown profile remains the durable source lens and source/governance policy:

--- ADVISOR PROFILE START ---

{advisor_profile}

--- ADVISOR PROFILE END ---
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an Advisory Board Hermes SOUL.md file to stdout.")
    parser.add_argument("advisor", choices=sorted(DISPLAY_NAMES))
    args = parser.parse_args()
    print(render_soul(args.advisor), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
