#!/usr/bin/env python3
"""PreToolUse hook: nepusti zapis do cudzieho WordPress kodu.

Blokuje Write/Edit/MultiEdit do wp-includes, wp-admin, wp-content/plugins
a do rodicovskej temy. Povoluje child temu a vlastne mu-pluginy ADM.

Vstup:  JSON na stdin (tool_name, tool_input, cwd, ...)
Vystup: JSON s permissionDecision na stdout, exit 0.
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BLOCKED = [
    (r"wp-includes/", "jadro WordPressu (wp-includes)"),
    (r"wp-admin/", "jadro WordPressu (wp-admin)"),
    (r"wp-content/plugins/", "cudzi plugin (wp-content/plugins)"),
    (r"wp-content/upgrade/", "docasny adresar aktualizacii"),
    (r"/wp-config\.php$", "wp-config.php"),
]

# Vynimky - sem zapisovat SMIE.
ALLOWED = [
    r"wp-content/themes/[^/]*-child/",
    r"wp-content/mu-plugins/adm-",
    r"wp-content/plugins/adm-",
]

PARENT_THEME = re.compile(r"wp-content/themes/(?P<slug>[^/]+)/")


def decision(allow: bool, reason: str = "") -> None:
    if allow:
        print(json.dumps({}))
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }, ensure_ascii=False))
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        decision(True)

    tool_input = payload.get("tool_input") or {}
    raw_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw_path:
        decision(True)

    path = raw_path.replace("\\", "/")

    for pattern in ALLOWED:
        if re.search(pattern, path):
            decision(True)

    for pattern, label in BLOCKED:
        if re.search(pattern, path):
            decision(False, (
                f"Zapis do '{raw_path}' je zakazany: {label}. "
                "Uprava cudzieho kodu sa prepise pri najblizsej aktualizacii. "
                "Presun zmenu do child temy (wp-content/themes/<tema>-child/), "
                "do vlastneho mu-pluginu (wp-content/mu-plugins/adm-*/), "
                "alebo pouzi filter/action hook. Toto pravidlo neobchadzaj cez Bash."
            ))

    match = PARENT_THEME.search(path)
    if match and not match.group("slug").endswith("-child"):
        decision(False, (
            f"Zapis do '{raw_path}' meni rodicovsku temu '{match.group('slug')}'. "
            f"Vytvor alebo pouzi child temu '{match.group('slug')}-child' "
            "a prepis subor tam."
        ))

    decision(True)


if __name__ == "__main__":
    main()
