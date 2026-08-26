"""Testy woo-mcp. Bezia v rezime fixtures - bez siete a bez e-shopu."""
import json
import os

import pytest

os.environ["WOO_MODE"] = "fixtures"
os.environ.pop("WOO_BASE_URL", None)

from woo_mcp.client import WooChyba, WooClient  # noqa: E402
from woo_mcp.server import mcp  # noqa: E402


async def zavolaj(nazov: str, **kwargs):
    """Zavola nastroj cez skutocne MCP rozhranie a rozbali JSON odpoved."""
    vysledok = await mcp.call_tool(nazov, kwargs)
    assert not vysledok.is_error, vysledok.content
    return json.loads(vysledok.content[0].text)


async def test_server_hlasi_bezpecny_default():
    stav = await zavolaj("server_status")
    assert stav["rezim"] == "fixtures"
    assert stav["zapis_povoleny"] is False


async def test_vsetky_nastroje_su_registrovane():
    nazvy = {t.name for t in await mcp.list_tools()}
    assert nazvy == {
        "server_status", "search_products", "get_product",
        "check_stock", "list_orders", "audit_seo", "update_product",
        "set_alt_text",
    }


async def test_kazdy_nastroj_ma_popis():
    for nastroj in await mcp.list_tools():
        assert nastroj.description, f"{nastroj.name} nema popis pre model"


async def test_citacie_nastroje_su_oznacene_ako_read_only():
    """Klient sa podla anotacii rozhoduje, kedy si pytat povolenie."""
    anotacie = {t.name: t.annotations for t in await mcp.list_tools()}
    for nazov in ("server_status", "search_products", "get_product",
                  "check_stock", "list_orders", "audit_seo"):
        assert anotacie[nazov].read_only_hint is True, nazov
    for nazov in ("update_product", "set_alt_text"):
        assert anotacie[nazov].read_only_hint is False, nazov
        assert anotacie[nazov].destructive_hint is True, nazov


async def test_hladanie_podla_sku():
    vysledok = await zavolaj("search_products", hladaj="XB48")
    assert vysledok["pocet"] == 1
    assert vysledok["produkty"][0]["sku"] == "XB48-0031"


async def test_vypis_je_orezany():
    """Kontrola, ze sa do kontextu nesype cely WooCommerce objekt."""
    vysledok = await zavolaj("search_products", limit=5)
    assert set(vysledok["produkty"][0]) == {
        "id", "sku", "nazov", "cena", "stav_skladu",
        "na_sklade", "kategorie", "pocet_obrazkov",
    }


async def test_produkt_podla_id_aj_sku():
    podla_id = await zavolaj("get_product", identifikator="101")
    podla_sku = await zavolaj("get_product", identifikator="XB47-0012")
    assert podla_id["id"] == podla_sku["id"] == 101
    assert "obrazky" in podla_id


async def test_neexistujuci_produkt_vrati_zrozumitelnu_chybu():
    vysledok = await zavolaj("get_product", identifikator="NEEXISTUJE")
    assert "chyba" in vysledok


async def test_sklad_hlasi_backorders():
    vysledok = await zavolaj("check_stock", sku="FLT-2200")
    assert vysledok["stav_skladu"] == "onbackorder"
    assert vysledok["backorders"] == "notify"


async def test_objednavky_sa_filtruju_podla_stavu():
    vsetky = await zavolaj("list_orders")
    rozpracovane = await zavolaj("list_orders", stav="processing")
    assert vsetky["pocet"] == 4
    assert rozpracovane["pocet"] == 2


async def test_audit_najde_chybajuci_alt_text():
    vysledok = await zavolaj("audit_seo")
    problemy = {n["sku"]: n["problemy"] for n in vysledok["nalezy"]}
    assert any("alt" in p for p in problemy["XB47-0012"])
    assert "XB48-0031" not in problemy, "cisty produkt nema byt v nalezoch"


async def test_audit_najde_rizikovu_diakritiku():
    vysledok = await zavolaj("audit_seo")
    problemy = {n["sku"]: " ".join(n["problemy"]) for n in vysledok["nalezy"]}
    assert "Š" in problemy["XB47-0012"]


async def test_audit_najde_dlhy_nazov_a_chybajuci_popis():
    vysledok = await zavolaj("audit_seo")
    problemy = {n["sku"]: " ".join(n["problemy"]) for n in vysledok["nalezy"]}
    assert "nad 70" in problemy["FLT-2200"]
    assert "kratky popis" in problemy["FLT-2200"]


async def test_zapis_mimo_live_iba_simuluje():
    vysledok = await zavolaj(
        "update_product", product_id=101, zmeny={"stock_quantity": 99}
    )
    assert vysledok["vykonane"] is False
    assert vysledok["nahlad_zmien"]["stock_quantity"] == {"predtym": 4, "potom": 99}


async def test_alt_text_mimo_live_iba_simuluje():
    vysledok = await zavolaj(
        "set_alt_text", product_id=101,
        alt_texty={"9101": "Šasi rám pre štvorkolku ATV 125 ccm, pohľad zboku"},
    )
    assert vysledok["vykonane"] is False
    assert vysledok["nahlad_zmien"]["9101"]["predtym"] == ""
    assert "štvorkolku" in vysledok["nahlad_zmien"]["9101"]["potom"]


async def test_alt_text_nechava_ostatne_obrazky_na_pokoji():
    """Produkt 104 ma jeden obrazok s altom a jeden bez. Meni sa len ten bez."""
    vysledok = await zavolaj(
        "set_alt_text", product_id=104,
        alt_texty={"9401": "Detská crossová prilba, čelný pohľad"},
    )
    assert list(vysledok["nahlad_zmien"]) == ["9401"]
    assert vysledok["zachovanych_obrazkov"] == 1


async def test_alt_text_odmietne_cudzi_obrazok():
    """ID obrazka z ineho produktu je typicky preklep - nesmie prejst ticho."""
    vysledok = await zavolaj(
        "set_alt_text", product_id=101, alt_texty={"9501": "Motorový olej"}
    )
    assert "chyba" in vysledok
    assert "9501" in vysledok["chyba"]


async def test_alt_text_rovnaky_text_nic_nemeni():
    vysledok = await zavolaj(
        "set_alt_text", product_id=104,
        alt_texty={"9402": "Detská crossová prilba, bočný pohľad"},
    )
    assert vysledok["nahlad_zmien"] == {}
    assert "bez_zmeny" in vysledok


async def test_update_product_varuje_pred_prepisom_galerie():
    """Kto posle images cez update_product, ma sa dozvediet, co to spravi."""
    vysledok = await zavolaj(
        "update_product", product_id=101,
        zmeny={"images": [{"id": 9101, "alt": "Šasi"}]},
    )
    assert "upozornenie" in vysledok
    assert "set_alt_text" in vysledok["upozornenie"]


def test_neplatny_rezim_zlyha_hned():
    os.environ["WOO_MODE"] = "vsetko-povolene"
    try:
        with pytest.raises(WooChyba, match="Neznamy WOO_MODE"):
            WooClient()
    finally:
        os.environ["WOO_MODE"] = "fixtures"


def test_live_bez_klucov_zlyha_hned():
    os.environ["WOO_MODE"] = "live"
    try:
        with pytest.raises(WooChyba, match="WOO_BASE_URL"):
            WooClient()
    finally:
        os.environ["WOO_MODE"] = "fixtures"
