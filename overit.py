#!/usr/bin/env python3
"""Kontrola celeho setupu. Spustenie:  python overit.py

Overuje, ze konfiguracia je platna a ze sa da odovzdat:
  - JSON subory su validne
  - ziadny subor nema UTF-8 BOM (rozbije parsovanie SKILL.md)
  - kazdy skill ma SKILL.md s poliami name a description
  - odkazy zo SKILL.md na references/ a scripts/ vedu na existujuce subory
  - kazdy subagent ma name, description a obmedzeny zoznam nastrojov
  - kazdy prikaz ma description
  - v repe nie su ziadne prihlasovacie udaje
  - nie je zapnuty ziadny plugin ani marketplace
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

KOREN = pathlib.Path(__file__).parent
PRESKOCIT = {".venv", "__pycache__", ".git", ".pytest_cache", "node_modules"}

# Vzory, ktore v repe nesmu byt.
TAJOMSTVA = [
    (r"ck_[0-9a-f]{40}", "WooCommerce consumer key"),
    (r"cs_[0-9a-f]{40}", "WooCommerce consumer secret"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "sukromny kluc"),
    (r"(?i)password\s*[=:]\s*['\"][^'\"]{6,}", "heslo v kode"),
]


def subory() -> list[pathlib.Path]:
    return [p for p in KOREN.rglob("*")
            if p.is_file() and not (PRESKOCIT & set(p.parts))]


def kontrola() -> list[str]:
    chyby: list[str] = []
    vsetky = subory()

    for p in vsetky:
        raw = p.read_bytes()
        rel = p.relative_to(KOREN)

        if raw.startswith(b"\xef\xbb\xbf"):
            chyby.append(f"{rel}: UTF-8 BOM")

        if p.suffix == ".json":
            try:
                json.loads(raw.decode("utf-8"))
            except Exception as e:
                chyby.append(f"{rel}: nevalidny JSON - {e}")

        if p.suffix in {".md", ".py", ".js", ".json", ".toml"} and p.name != ".env.example":
            text = raw.decode("utf-8", errors="replace")
            for vzor, popis in TAJOMSTVA:
                if re.search(vzor, text):
                    chyby.append(f"{rel}: vyzera to ako {popis}")

    # skills
    skills = sorted((KOREN / ".claude/skills").iterdir())
    for s in skills:
        sk = s / "SKILL.md"
        if not sk.exists():
            chyby.append(f"{s.name}: chyba SKILL.md")
            continue
        t = sk.read_text(encoding="utf-8")
        if not t.startswith("---"):
            chyby.append(f"{s.name}/SKILL.md: nezacina frontmatterom")
            continue
        fm = t.split("---")[1]
        for pole in ("name:", "description:"):
            if pole not in fm:
                chyby.append(f"{s.name}/SKILL.md: chyba {pole}")
        nazov = re.search(r"^name:\s*(.+)$", fm, re.M)
        if nazov and nazov.group(1).strip() != s.name:
            chyby.append(f"{s.name}/SKILL.md: name '{nazov.group(1).strip()}' "
                         f"nesedi s nazvom adresara")
        for odkaz in re.findall(r"\]\((references/[^)]+|scripts/[^)]+)\)", t):
            if not (s / odkaz).exists():
                chyby.append(f"{s.name}/SKILL.md: odkaz na neexistujuci {odkaz}")

    # subagenti
    agenti = sorted((KOREN / ".claude/agents").glob("*.md"))
    for a in agenti:
        fm = a.read_text(encoding="utf-8").split("---")[1]
        for pole in ("name:", "description:", "tools:"):
            if pole not in fm:
                chyby.append(f"agents/{a.name}: chyba {pole}")
        if re.search(r"^tools:\s*\*\s*$", fm, re.M):
            chyby.append(f"agents/{a.name}: ma vsetky nastroje, ma mat obmedzeny zoznam")

    # prikazy
    prikazy = sorted((KOREN / ".claude/commands").glob("*.md"))
    for c in prikazy:
        if "description:" not in c.read_text(encoding="utf-8").split("---")[1]:
            chyby.append(f"commands/{c.name}: chyba description")

    # ziadne pluginy
    nastavenia = json.loads((KOREN / ".claude/settings.json").read_text(encoding="utf-8"))
    for zakazane in ("enabledPlugins", "extraKnownMarketplaces"):
        if zakazane in nastavenia:
            chyby.append(f".claude/settings.json: obsahuje {zakazane} - zadanie pluginy zakazuje")

    print(f"suborov: {len(vsetky)} | skillov: {len(skills)} | "
          f"subagentov: {len(agenti)} | prikazov: {len(prikazy)}")
    return chyby


def main() -> int:
    chyby = kontrola()
    if chyby:
        print(f"\n{len(chyby)} nalezov:")
        for c in chyby:
            print("  -", c)
        return 1
    print("bez nalezov - setup je v poriadku")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
