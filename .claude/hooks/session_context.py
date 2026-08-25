#!/usr/bin/env python3
"""SessionStart hook: vpichne do kontextu stav projektu.

Agent tak na zaciatku vie, v akom rezime bezi woo MCP, ci existuje .env
a na akej vetve sa pracuje - bez toho, aby to musel zistovat nastrojmi.
"""
import json
import os
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()

MODE_POPIS = {
    "fixtures": "OFFLINE demo data z mcp-servers/woo-mcp/fixtures/ - "
                "cisla NIE su stav realneho e-shopu, neprezentuj ich klientovi",
    "dry-run": "cita naozivo, zapisy sa iba simuluju a vracia sa nahlad zmeny",
    "live": "PLNY ZAPIS do e-shopu - kazdy update meni realne data",
}


def woo_mode() -> str:
    mode = os.environ.get("WOO_MODE", "").strip()
    env_file = ROOT / ".env"
    if not mode and env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("WOO_MODE="):
                mode = line.split("=", 1)[1].strip()
                break
    return mode or "fixtures"


def git_branch() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                             cwd=ROOT, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "-"
    except (OSError, subprocess.SubprocessError):
        return "-"


def spocitaj(podadresar: str, vzor: str) -> int:
    cesta = ROOT / ".claude" / podadresar
    return len(list(cesta.glob(vzor))) if cesta.exists() else 0


def main() -> None:
    mode = woo_mode()
    riadky = [
        "## Stav projektu (SessionStart hook)",
        "",
        f"- woo MCP rezim: **{mode}** - {MODE_POPIS.get(mode, 'neznamy rezim')}",
        f"- .env: {'existuje' if (ROOT / '.env').exists() else 'CHYBA - skopiruj .env.example na .env'}",
        f"- git vetva: {git_branch()}",
        f"- k dispozicii: {spocitaj('skills', '*/SKILL.md')} skillov, "
        f"{spocitaj('agents', '*.md')} subagentov, "
        f"{spocitaj('commands', '*.md')} prikazov",
    ]
    if mode == "live":
        riadky += ["", "> POZOR: rezim `live`. Pred kazdym hromadnym zapisom si vyziadaj "
                       "potvrdenie od pouzivatela a najprv ukaz nahlad."]

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(riadky),
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
