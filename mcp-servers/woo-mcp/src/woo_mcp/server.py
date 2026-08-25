"""MCP server nad WooCommerce REST API.

Spustenie:  uv --directory mcp-servers/woo-mcp run woo-mcp
Rezim riadi premenna WOO_MODE (fixtures | dry-run | live), default fixtures.
"""
from __future__ import annotations

import re
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from .client import WooChyba, WooClient

mcp = MCPServer(
    "woo",
    instructions=(
        "Nastroje nad WooCommerce e-shopom. Skor nez ukazes akekolvek cisla "
        "pouzivatelovi alebo nieco zmenis, zavolaj server_status a over rezim. "
        "V rezime fixtures su data demo, nie stav realneho e-shopu."
    ),
)

# Anotacie hovoria klientovi, ktore nastroje su bezpecne volat automaticky
# a ktore menia data. Claude Code podla nich vie, kedy sa pytat na povolenie.
IBA_CITANIE = ToolAnnotations(read_only_hint=True, open_world_hint=True)
ZAPIS = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True)

_klient: WooClient | None = None


def klient() -> WooClient:
    global _klient
    if _klient is None:
        _klient = WooClient()
    return _klient


def _strucne(p: dict[str, Any]) -> dict[str, Any]:
    """Orez produkt na polia, ktore model naozaj potrebuje.

    WooCommerce vracia na produkt aj 60+ poli. Keby sme ich vratili vsetky,
    jeden vypis 20 produktov zabere niekolko tisic tokenov kontextu.
    """
    return {
        "id": p.get("id"),
        "sku": p.get("sku"),
        "nazov": p.get("name"),
        "cena": p.get("price"),
        "stav_skladu": p.get("stock_status"),
        "na_sklade": p.get("stock_quantity"),
        "kategorie": [k.get("name") for k in p.get("categories", [])],
        "pocet_obrazkov": len(p.get("images", [])),
    }


@mcp.tool(annotations=IBA_CITANIE)
def server_status() -> dict[str, Any]:
    """Zisti, v akom rezime server bezi a na aky e-shop je napojeny.

    Zavolaj to skor, nez zacnes cokolvek menit alebo nez cisla ukazes klientovi.
    """
    try:
        k = klient()
    except WooChyba as chyba:
        return {"chyba": str(chyba)}
    return {
        "rezim": k.mode,
        "eshop": k.maskovana_domena(),
        "zapis_povoleny": k.zapis_povoleny,
        "vyznam": {
            "fixtures": "offline demo data, NIE su to realne cisla e-shopu",
            "dry-run": "cita naozivo, zapisy len simuluje",
            "live": "plny zapis do e-shopu",
        }[k.mode],
    }


@mcp.tool(annotations=IBA_CITANIE)
def search_products(hladaj: str = "", limit: int = 20) -> dict[str, Any]:
    """Najdi produkty podla nazvu alebo SKU. Vracia skrateny vypis.

    hladaj: cast nazvu alebo SKU, prazdne = prvych `limit` produktov
    limit:  max pocet vysledkov (rozumne do 50)
    """
    try:
        data = klient().produkty(hladaj, limit)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}
    return {"pocet": len(data), "produkty": [_strucne(p) for p in data]}


@mcp.tool(annotations=IBA_CITANIE)
def get_product(identifikator: str) -> dict[str, Any]:
    """Nacitaj jeden produkt podla ID alebo SKU vratane popisov a obrazkov."""
    try:
        p = klient().produkt(identifikator)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}
    if p is None:
        return {"chyba": f"Produkt '{identifikator}' sa nenasiel."}
    detail = _strucne(p)
    detail["kratky_popis"] = p.get("short_description", "")
    detail["popis"] = p.get("description", "")
    detail["obrazky"] = [
        {"id": o.get("id"), "src": o.get("src"), "alt": o.get("alt", "")}
        for o in p.get("images", [])
    ]
    return detail


@mcp.tool(annotations=IBA_CITANIE)
def check_stock(sku: str) -> dict[str, Any]:
    """Over stav skladu jedneho produktu podla SKU."""
    try:
        p = klient().produkt(sku)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}
    if p is None:
        return {"chyba": f"SKU '{sku}' sa nenaslo."}
    return {
        "sku": p.get("sku"),
        "nazov": p.get("name"),
        "stav_skladu": p.get("stock_status"),
        "na_sklade": p.get("stock_quantity"),
        "backorders": p.get("backorders", "no"),
    }


@mcp.tool(annotations=IBA_CITANIE)
def list_orders(stav: str = "any", limit: int = 20) -> dict[str, Any]:
    """Vypis objednavky. stav: any, processing, completed, on-hold, cancelled."""
    try:
        data = klient().objednavky(stav, limit)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}
    return {
        "pocet": len(data),
        "objednavky": [
            {
                "id": o.get("id"),
                "stav": o.get("status"),
                "suma": o.get("total"),
                "mena": o.get("currency"),
                "datum": o.get("date_created"),
                "poloziek": len(o.get("line_items", [])),
            }
            for o in data
        ],
    }


# Znaky, ktore vypadnu, ked je font subset bez slovenskej diakritiky.
# Typicky Adobe web kit: velke S s makcenom sa nevykresli.
RIZIKOVE_ZNAKY = "ŠČŤĎŇĽŔŽÝÁÍÉÚÔÄ"


@mcp.tool(annotations=IBA_CITANIE)
def audit_seo(limit: int = 50) -> dict[str, Any]:
    """Najdi produkty s chybami, ktore skodia SEO a zobrazeniu.

    Kontroluje: chybajuci alt text obrazkov, chybajuci kratky popis,
    prilis dlhy nazov (nad 70 znakov) a rizikovu diakritiku v nazve.
    """
    try:
        data = klient().produkty("", limit)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}

    nalezy: list[dict[str, Any]] = []
    for p in data:
        problemy = []
        bez_altu = [o for o in p.get("images", []) if not (o.get("alt") or "").strip()]
        if bez_altu:
            problemy.append(f"{len(bez_altu)} obrazkov bez alt textu")
        if not (p.get("short_description") or "").strip():
            problemy.append("chyba kratky popis")
        nazov = p.get("name", "")
        if len(nazov) > 70:
            problemy.append(f"nazov ma {len(nazov)} znakov (nad 70 sa v Google oreze)")
        rizikove = sorted({z for z in nazov if z in RIZIKOVE_ZNAKY})
        if rizikove:
            problemy.append(
                "nazov obsahuje znaky " + ", ".join(rizikove)
                + " - over, ci ich font na webe vykresluje (subset bez diakritiky "
                  "ich zobrazi ako prazdne miesto)"
            )
        if not re.search(r"\d", p.get("sku", "")) and p.get("sku"):
            problemy.append("SKU bez cisla - over konvenciu")
        if problemy:
            nalezy.append({
                "id": p.get("id"),
                "sku": p.get("sku"),
                "nazov": nazov,
                "problemy": problemy,
            })

    return {
        "skontrolovanych": len(data),
        "s_problemom": len(nalezy),
        "nalezy": nalezy,
    }


@mcp.tool(annotations=ZAPIS)
def update_product(product_id: int, zmeny: dict[str, Any]) -> dict[str, Any]:
    """Uprav produkt. V rezime fixtures a dry-run vrati IBA nahlad zmeny.

    product_id: ciselne ID produktu
    zmeny: slovnik poli WooCommerce REST, napr.
           {"short_description": "...", "stock_quantity": 5}
    """
    try:
        return klient().uprav_produkt(product_id, zmeny)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
