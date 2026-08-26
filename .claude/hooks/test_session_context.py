#!/usr/bin/env python3
"""Test hooku session_context.py. Spustenie: python .claude/hooks/test_session_context.py

Posledny test je ten podstatny: rezim `store` pribudol do MCP klienta, ale nie
do hlasenia hooku, takze cela relacia zacinala hlaskou 'neznamy rezim'. Odvtedy
sa oba zoznamy porovnavaju.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

HOOK = pathlib.Path(__file__).with_name("session_context.py")
KOREN = HOOK.parents[2]
KLIENT = KOREN / "mcp-servers/woo-mcp/src/woo_mcp/client.py"


def spusti(mode: str) -> str:
    """Zavola hook s danym WOO_MODE a vrati vpichnuty kontext.

    Prostredie sa dedi a prepisu sa len dve premenne. Podvrhnut cely env
    sa neda - na Windows sa Python bez SystemRoot ani nenaskrutkuje.
    """
    vystup = subprocess.run(
        [sys.executable, str(HOOK)], input="{}",
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "WOO_MODE": mode, "CLAUDE_PROJECT_DIR": str(KOREN)},
    )
    if vystup.returncode != 0 or not vystup.stdout.strip():
        raise AssertionError(
            f"hook zlyhal pre WOO_MODE={mode!r} (kod {vystup.returncode}): "
            f"{vystup.stderr.strip() or 'ziadny vystup'}"
        )
    data = json.loads(vystup.stdout)
    assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    return data["hookSpecificOutput"]["additionalContext"]


def rezimy_klienta() -> set[str]:
    """Vytiahne PLATNE_REZIMY z klienta bez importu - hook je bez zavislosti."""
    zdroj = KLIENT.read_text(encoding="utf-8")
    zoznam = re.search(r"PLATNE_REZIMY\s*=\s*\(([^)]*)\)", zdroj).group(1)
    return set(re.findall(r"[\"']([^\"']+)[\"']", zoznam))


CASES = [
    ("fixtures hlasi demo data", "fixtures", "OFFLINE demo data"),
    ("store hlasi realne data", "store", "REALNE data"),
    ("store priznava, co nevracia", "store", "objednavky"),
    ("dry-run hlasi simulaciu", "dry-run", "simuluju"),
    ("live hlasi plny zapis", "live", "PLNY ZAPIS"),
    ("live prida varovanie", "live", "POZOR"),
    ("preklep sa oznaci", "vsetko-povolene", "NEZNAMY rezim"),
    ("preklep vypise povolene", "vsetko-povolene", "dry-run"),
]


def main() -> int:
    zlyhalo = 0

    for popis, mode, ocakavane in CASES:
        kontext = spusti(mode)
        if ocakavane in kontext:
            print(f"OK    {popis:34} -> obsahuje '{ocakavane}'")
        else:
            zlyhalo += 1
            print(f"CHYBA {popis:34} -> chyba '{ocakavane}'")

    # Ziadny platny rezim nesmie skoncit ako neznamy.
    for mode in sorted(rezimy_klienta()):
        kontext = spusti(mode)
        popis = f"klient pozna '{mode}'"
        if "NEZNAMY rezim" in kontext:
            zlyhalo += 1
            print(f"CHYBA {popis:34} -> hook ho nepozna")
        else:
            print(f"OK    {popis:34} -> hook ho pozna")

    spolu = len(CASES) + len(rezimy_klienta())
    print(f"\n{spolu - zlyhalo}/{spolu} testov preslo")
    return 1 if zlyhalo else 0


if __name__ == "__main__":
    raise SystemExit(main())
