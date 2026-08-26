"""MCP server nad WooCommerce REST API.

Spustenie:  uv --directory mcp-servers/woo-mcp run woo-mcp
Rezim riadi WOO_MODE (fixtures | store | dry-run | live), default fixtures.
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
        "V rezime fixtures su data demo, nie stav realneho e-shopu. Rezim store "
        "cita realne data verejne, bez klucov, a nic nezapise."
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
        "cita_naozivo": k.cita_naozivo,
        "vyznam": {
            "fixtures": "offline demo data, NIE su to realne cisla e-shopu",
            "store": "verejne Store API, realne data e-shopu, iba citanie bez klucov",
            "dry-run": "wc/v3 naozivo, zapisy len simuluje",
            "live": "plny zapis do e-shopu",
        }.get(k.mode, "neznamy rezim"),
    }


@mcp.tool(annotations=IBA_CITANIE)
def search_products(hladaj: str = "", limit: int = 20) -> dict[str, Any]:
    """Najdi produkty podla nazvu alebo SKU. Vracia skrateny vypis.

    hladaj: cast nazvu alebo SKU, prazdne = prvych `limit` produktov
    limit:  max pocet vysledkov; nad 100 sa automaticky strankuje
    """
    try:
        data, neuplne = klient().produkty(hladaj, limit)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}
    vysledok: dict[str, Any] = {
        "pocet": len(data),
        "produkty": [_strucne(p) for p in data],
    }
    if neuplne:
        vysledok["upozornenie"] = (
            "Vysledok je orezany poistkou strankovania - nie je to cely katalog. "
            "Neprezentuj ho ako uplny."
        )
    return vysledok


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


def _bez_html(text: str) -> str:
    """Store API vracia popisy ako HTML. Prazdny odstavec nie je popis."""
    return re.sub(r"<[^>]+>", "", text or "").replace("&nbsp;", " ").strip()


@mcp.tool(annotations=IBA_CITANIE)
def audit_seo(limit: int = 200, zahrn_varianty: bool = True) -> dict[str, Any]:
    """Najdi produkty s chybami, ktore skodia SEO a zobrazeniu.

    Kontroluje: chybajuci alt text obrazkov, chybajuci kratky popis,
    prilis dlhy nazov (nad 70 znakov) a rizikovu diakritiku v nazve.

    limit: kolko produktov prejst; nad 100 sa automaticky strankuje
    zahrn_varianty: pri variabilnych produktoch nacitat aj fotky jednotlivych
        variantov. Fotka varianty sa zobrazi az po prepnuti farby, takze audit
        bez tohto ju nikdy neuvidi. Stoji to jednu poziadavku na variant.
    """
    try:
        k = klient()
        data, neuplne = k.produkty("", limit)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}

    nalezy: list[dict[str, Any]] = []
    obrazkov_spolu = 0
    obrazkov_bez_altu = 0
    variantov_skontrolovanych = 0
    produktov_s_neuplnymi_variantmi = 0

    for p in data:
        problemy = []
        obrazky = list(p.get("images", []))

        if zahrn_varianty and p.get("type") == "variable":
            try:
                nacitane, problemy_variantov = k.varianty(p)
            except WooChyba as chyba:
                problemy.append(f"varianty sa nepodarilo nacitat ({chyba}) - "
                                "skontrolovany iba rodicovsky produkt")
                produktov_s_neuplnymi_variantmi += 1
            else:
                for v in nacitane:
                    variantov_skontrolovanych += 1
                    obrazky.extend(v.get("images", []))
                if problemy_variantov:
                    problemy.extend(problemy_variantov)
                    produktov_s_neuplnymi_variantmi += 1

        obrazkov_spolu += len(obrazky)
        bez_altu = [o for o in obrazky if not (o.get("alt") or "").strip()]
        obrazkov_bez_altu += len(bez_altu)
        if bez_altu:
            problemy.append(f"{len(bez_altu)} z {len(obrazky)} obrazkov bez alt textu")

        if not _bez_html(p.get("short_description", "")):
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

        if p.get("sku") and not re.search(r"\d", p.get("sku", "")):
            problemy.append("SKU bez cisla - over konvenciu")

        if problemy:
            nalezy.append({
                "id": p.get("id"),
                "sku": p.get("sku"),
                "nazov": nazov,
                "typ": p.get("type"),
                "problemy": problemy,
            })

    vysledok: dict[str, Any] = {
        "rezim": k.mode,
        "skontrolovanych_produktov": len(data),
        "skontrolovanych_variantov": variantov_skontrolovanych,
        "obrazkov_spolu": obrazkov_spolu,
        "obrazkov_bez_alt_textu": obrazkov_bez_altu,
        "s_problemom": len(nalezy),
        "nalezy": nalezy,
    }
    upozornenia: list[str] = []
    if neuplne:
        upozornenia.append(
            "Audit je orezany poistkou strankovania - nepresiel cely katalog."
        )
    if produktov_s_neuplnymi_variantmi:
        # Nizsi pocet obrazkov, nez je skutocnost, je horsi nez hlasna chyba -
        # audit by inak vyzeral uplne a hlasil menej nalezov, nez ich je.
        upozornenia.append(
            f"Pri {produktov_s_neuplnymi_variantmi} produktoch sa nepodarilo "
            "nacitat vsetky varianty - pocet obrazkov je nizsi, nez je "
            "skutocnost. Podrobnosti su v poli 'problemy' u konkretnych produktov."
        )
    if upozornenia:
        vysledok["upozornenie"] = " ".join(upozornenia)
    if not zahrn_varianty:
        vysledok["nekontrolovane"] = "fotky variantov (zahrn_varianty=False)"
    return vysledok


@mcp.tool(annotations=ZAPIS)
def update_product(product_id: int, zmeny: dict[str, Any]) -> dict[str, Any]:
    """Uprav produkt. Mimo rezimu live vrati IBA nahlad zmeny.

    V rezime store zlyha - Store API je iba na citanie.

    product_id: ciselne ID produktu
    zmeny: slovnik poli WooCommerce REST, napr.
           {"short_description": "...", "stock_quantity": 5}

    Na alt texty tento nastroj NEPOUZIVAJ - pole `images` nahradi celu galeriu
    produktu. Na to je set_alt_text.
    """
    try:
        return klient().uprav_produkt(product_id, zmeny)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}


@mcp.tool(annotations=ZAPIS)
def set_alt_text(product_id: int, alt_texty: dict[str, str]) -> dict[str, Any]:
    """Doplni alebo prepise alt texty obrazkov produktu. Mimo `live` iba nahlad.

    product_id: ciselne ID produktu
    alt_texty: {"<id obrazka>": "alt text"}. ID obrazkov vrati get_product
        v poli `obrazky`. Poslat sa daju aj len niektore - zvysok galerie
        zostane nedotknuty.

    Preco samostatny nastroj a nie update_product: WooCommerce pri zapise pola
    `images` nahradi CELU galeriu tym, co dostane. Kto posle len menene obrazky,
    zvysne fotky z produktu zmaze. Tento nastroj aktualnu galeriu najprv
    nacita, doplni do nej nove alt texty a posle ju celu.

    Alt text pis ako popis toho, co je na fotke, vratane pohladu - nie nazov
    suboru ani zopakovany nazov produktu.
    """
    try:
        return klient().nastav_alt_texty(product_id, alt_texty)
    except WooChyba as chyba:
        return {"chyba": str(chyba)}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
