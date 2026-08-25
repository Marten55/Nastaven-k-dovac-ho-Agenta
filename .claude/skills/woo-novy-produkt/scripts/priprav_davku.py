#!/usr/bin/env python3
"""Priprav davku produktov z CSV a skontroluj ju este pred zapisom do e-shopu.

Pouzitie:
    python priprav_davku.py produkty.csv            # iba kontrola
    python priprav_davku.py produkty.csv --json out.json

CSV musi mat hlavicku so stlpcami:
    sku,name,regular_price,short_description,stock_quantity,categories,alt

`categories` a `alt` mozu obsahovat viac hodnot oddelenych bodkociarkou.

Skript nic nezapisuje. Vystupny JSON sa da poslat do mcp__woo__update_product.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

MAX_DLZKA_NAZVU = 70
RIZIKOVE_ZNAKY = set("ŠČŤĎŇĽŔŽÝÁÍÉÚÔÄ")


def skontroluj(riadok: dict[str, str], cislo: int) -> list[str]:
    chyby: list[str] = []
    sku = (riadok.get("sku") or "").strip()
    nazov = (riadok.get("name") or "").strip()

    if not sku:
        chyby.append("chyba SKU")
    elif not any(z.isdigit() for z in sku):
        chyby.append(f"SKU '{sku}' neobsahuje cislo - over konvenciu")

    if not nazov:
        chyby.append("chyba nazov")
    elif len(nazov) > MAX_DLZKA_NAZVU:
        chyby.append(f"nazov ma {len(nazov)} znakov (limit {MAX_DLZKA_NAZVU})")

    if not (riadok.get("short_description") or "").strip():
        chyby.append("chyba kratky popis")

    cena = (riadok.get("regular_price") or "").strip()
    if not cena:
        chyby.append("chyba cena")
    else:
        if "," in cena:
            chyby.append(f"cena '{cena}' ma desatinnu ciarku - WooCommerce chce bodku")
        try:
            float(cena.replace(",", "."))
        except ValueError:
            chyby.append(f"cena '{cena}' nie je cislo")

    if not (riadok.get("alt") or "").strip():
        chyby.append("chyba alt text")

    rizikove = sorted(set(nazov) & RIZIKOVE_ZNAKY)
    if rizikove:
        chyby.append(
            "nazov obsahuje " + ", ".join(rizikove)
            + " - over, ci ich font na webe vykresluje"
        )
    return chyby


def na_woo(riadok: dict[str, str]) -> dict:
    return {
        "sku": riadok["sku"].strip(),
        "name": riadok["name"].strip(),
        "regular_price": riadok["regular_price"].strip().replace(",", "."),
        "short_description": riadok.get("short_description", "").strip(),
        "stock_quantity": int(riadok["stock_quantity"]) if riadok.get("stock_quantity", "").strip() else None,
        "categories": [c.strip() for c in (riadok.get("categories") or "").split(";") if c.strip()],
        "alt_texty": [a.strip() for a in (riadok.get("alt") or "").split(";") if a.strip()],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_subor", type=pathlib.Path)
    parser.add_argument("--json", type=pathlib.Path, help="kam ulozit pripravenu davku")
    args = parser.parse_args()

    if not args.csv_subor.exists():
        print(f"Subor {args.csv_subor} neexistuje.", file=sys.stderr)
        return 2

    with args.csv_subor.open(encoding="utf-8-sig", newline="") as f:
        riadky = list(csv.DictReader(f))

    davka, chybnych, videne_sku = [], 0, set()
    for i, riadok in enumerate(riadky, start=2):
        chyby = skontroluj(riadok, i)
        sku = (riadok.get("sku") or "").strip()
        if sku in videne_sku:
            chyby.append(f"duplicitne SKU '{sku}' v CSV")
        videne_sku.add(sku)

        if chyby:
            chybnych += 1
            print(f"riadok {i} ({sku or '?'}):")
            for ch in chyby:
                print(f"    - {ch}")
        else:
            davka.append(na_woo(riadok))

    print(f"\n{len(riadky)} riadkov, {len(davka)} v poriadku, {chybnych} s chybou")

    if args.json and davka:
        args.json.write_text(json.dumps(davka, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Davka ulozena do {args.json}")
    if chybnych:
        print("\nChybne riadky oprav v CSV a spusti znova. Nic sa nezapisalo.")
    return 1 if chybnych else 0


if __name__ == "__main__":
    raise SystemExit(main())
