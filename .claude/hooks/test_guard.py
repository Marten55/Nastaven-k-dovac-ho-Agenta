#!/usr/bin/env python3
"""Test hooku guard_wp_core.py. Spustenie: python .claude/hooks/test_guard.py"""
import json
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).with_name("guard_wp_core.py")

CASES = [
    ("Windows cesta do cudzieho pluginu", r"C:\web\wp-content\plugins\woocommerce\woocommerce.php", "deny"),
    ("unix cesta do cudzieho pluginu", "/var/www/wp-content/plugins/elementor/elementor.php", "deny"),
    ("vlastny ADM plugin", "/var/www/wp-content/plugins/adm-tweaks/adm-tweaks.php", "allow"),
    ("child tema", "/var/www/wp-content/themes/astra-child/functions.php", "allow"),
    ("rodicovska tema", "/var/www/wp-content/themes/astra/style.css", "deny"),
    ("wp-includes", "/var/www/wp-includes/functions.php", "deny"),
    ("wp-admin", "/var/www/wp-admin/includes/post.php", "deny"),
    ("wp-config.php", "/var/www/wp-config.php", "deny"),
    ("mu-plugin ADM", "/var/www/wp-content/mu-plugins/adm-hotfix/loader.php", "allow"),
    ("bezny subor v repe", "docs/report.md", "allow"),
]


def run(path: str) -> str:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": path}})
    out = subprocess.run([sys.executable, str(HOOK)], input=payload,
                         capture_output=True, text=True, encoding="utf-8")
    return "deny" if "permissionDecision" in out.stdout else "allow"


def main() -> int:
    failed = 0
    for label, path, expected in CASES:
        got = run(path)
        if got != expected:
            failed += 1
            print(f"CHYBA {label:36} ocakavane={expected} dostal={got}")
        else:
            print(f"OK    {label:36} -> {got}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} testov preslo")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
