"""Testy rezimu `store`, strankovania a variantov.

HTTP je mockovane - testy nechodia na ziadny e-shop.
"""
import json
import os

import httpx
import pytest

from woo_mcp.client import MAX_PER_PAGE, WooChyba, WooClient


# --- pomocky ------------------------------------------------------------


class FalosnaOdpoved:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = json.dumps(data)

    def json(self):
        return self._data


def store_produkt(pid, nazov="Test", sku="T-1", obrazky=None, typ="simple",
                  varianty=None, popis="<p>Popis.</p>"):
    """Tvar, aky naozaj vracia WooCommerce Store API."""
    return {
        "id": pid,
        "name": nazov,
        "sku": sku,
        "type": typ,
        "short_description": popis,
        "description": "<p>Dlhy popis.</p>",
        "prices": {"price": "89999", "currency_minor_unit": 2},
        "is_in_stock": True,
        "on_backorder": False,
        "categories": [{"id": 1, "name": "Stvorkolky"}],
        "images": obrazky if obrazky is not None else [
            {"id": 900 + pid, "src": "https://x/a.jpg", "alt": ""}
        ],
        "variations": varianty or [],
    }


@pytest.fixture
def store_klient(monkeypatch):
    monkeypatch.setenv("WOO_MODE", "store")
    monkeypatch.setenv("WOO_BASE_URL", "https://example-shop.sk")
    monkeypatch.delenv("WOO_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("WOO_CONSUMER_SECRET", raising=False)
    return WooClient()


# --- rezim store --------------------------------------------------------


def test_store_nepotrebuje_kluce(store_klient):
    assert store_klient.mode == "store"
    assert store_klient.zapis_povoleny is False
    assert store_klient.cita_naozivo is True


def test_store_bez_adresy_zlyha(monkeypatch):
    monkeypatch.setenv("WOO_MODE", "store")
    monkeypatch.delenv("WOO_BASE_URL", raising=False)
    with pytest.raises(WooChyba, match="WOO_BASE_URL"):
        WooClient()


def test_store_nepridava_autentifikaciu(store_klient, monkeypatch):
    zachytene = {}

    def falosny_get(url, **kw):
        zachytene["url"] = url
        zachytene["auth"] = kw.get("auth")
        return FalosnaOdpoved([store_produkt(1)])

    monkeypatch.setattr(httpx, "get", falosny_get)
    store_klient.produkty("", 5)
    assert "/wc/store/v1/products" in zachytene["url"]
    assert zachytene["auth"] is None, "Store API sa nesmie volat s klucmi"


def test_store_tvar_sa_normalizuje(store_klient, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: FalosnaOdpoved(
        [store_produkt(101, nazov="Minibike", sku="XB18")]))
    produkty, _ = store_klient.produkty("", 5)
    p = produkty[0]
    assert p["name"] == "Minibike"
    assert p["sku"] == "XB18"
    assert p["price"] == "899.99", "cena zo Store API je v centoch, ma sa prepocitat"
    assert p["stock_status"] == "instock"
    assert p["images"][0]["alt"] == ""
    assert p["categories"][0]["name"] == "Stvorkolky"


def test_store_neumoznuje_zapis(store_klient):
    with pytest.raises(WooChyba, match="iba na citanie"):
        store_klient.uprav_produkt(101, {"stock_quantity": 5})


def test_store_neumoznuje_objednavky(store_klient):
    with pytest.raises(WooChyba, match="bezpecnostna diera"):
        store_klient.objednavky()


# --- strankovanie -------------------------------------------------------


def test_strankovanie_prejde_viac_stran(store_klient, monkeypatch):
    """Katalog nad 100 produktov sa nesmie ticho orezat."""
    volania = []

    def falosny_get(url, params=None, **kw):
        volania.append(params)
        strana = params["page"]
        if strana == 1:
            return FalosnaOdpoved([store_produkt(i) for i in range(MAX_PER_PAGE)])
        if strana == 2:
            return FalosnaOdpoved([store_produkt(1000 + i) for i in range(27)])
        return FalosnaOdpoved([])

    monkeypatch.setattr(httpx, "get", falosny_get)
    produkty, neuplne = store_klient.produkty("", 200)

    assert len(produkty) == 127, "ma vratit vsetkych 127, nie prvych 100"
    assert neuplne is False
    assert volania[0]["per_page"] == 100
    assert volania[1]["page"] == 2


def test_strankovanie_respektuje_limit(store_klient, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, params=None, **kw: FalosnaOdpoved(
        [store_produkt(i) for i in range(params["per_page"])]))
    produkty, _ = store_klient.produkty("", 30)
    assert len(produkty) == 30


def test_strankovanie_ma_poistku(store_klient, monkeypatch):
    """Server, ktory vracia stale plnu stranku, nesmie tocit donekonecna."""
    monkeypatch.setattr(httpx, "get", lambda url, params=None, **kw: FalosnaOdpoved(
        [store_produkt(i) for i in range(params["per_page"])]))
    produkty, neuplne = store_klient.produkty("", 10_000)
    assert neuplne is True, "orezany vysledok sa musi oznacit"
    assert len(produkty) <= 20 * MAX_PER_PAGE


# --- wc/v3 filtruje kos -------------------------------------------------


def test_v3_filtruje_na_publikovane(monkeypatch):
    monkeypatch.setenv("WOO_MODE", "dry-run")
    monkeypatch.setenv("WOO_BASE_URL", "https://example-shop.sk")
    monkeypatch.setenv("WOO_CONSUMER_KEY", "ck_test")
    monkeypatch.setenv("WOO_CONSUMER_SECRET", "cs_test")
    zachytene = {}

    def falosny_get(url, params=None, **kw):
        zachytene.update(params or {})
        return FalosnaOdpoved([])

    monkeypatch.setattr(httpx, "get", falosny_get)
    WooClient().produkty("", 10)
    assert zachytene.get("status") == "publish", \
        "bez tohto vracia wc/v3 aj produkty v kosi"


def test_store_nefiltruje_status(store_klient, monkeypatch):
    zachytene = {}
    monkeypatch.setattr(httpx, "get", lambda url, params=None, **kw: (
        zachytene.update(params or {}), FalosnaOdpoved([]))[1])
    store_klient.produkty("", 10)
    assert "status" not in zachytene, "Store API parameter status nepozna"


# --- varianty -----------------------------------------------------------


def test_varianty_sa_nacitaju_s_vlastnymi_obrazkami(store_klient, monkeypatch):
    rodic = store_produkt(4016, typ="variable",
                          varianty=[{"id": 4025}, {"id": 4026}])

    def falosny_get(url, params=None, **kw):
        if url.endswith("/products/4025"):
            return FalosnaOdpoved(store_produkt(
                4025, obrazky=[{"id": 2105, "src": "x", "alt": ""}]))
        if url.endswith("/products/4026"):
            return FalosnaOdpoved(store_produkt(
                4026, obrazky=[{"id": 2106, "src": "x", "alt": "Modra varianta"}]))
        return FalosnaOdpoved([rodic])

    monkeypatch.setattr(httpx, "get", falosny_get)
    produkty, _ = store_klient.produkty("", 5)
    varianty = store_klient.varianty(produkty[0])

    assert len(varianty) == 2
    assert varianty[0]["images"][0]["alt"] == ""
    assert varianty[1]["images"][0]["alt"] == "Modra varianta"


def test_jednoduchy_produkt_nema_varianty(store_klient, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: FalosnaOdpoved([store_produkt(1)]))
    produkty, _ = store_klient.produkty("", 5)
    assert store_klient.varianty(produkty[0]) == []


# --- audit cez MCP rozhranie -------------------------------------------


async def test_audit_zapocita_obrazky_variantov(monkeypatch):
    """Fotka varianty sa zobrazi az po prepnuti farby - audit ju musi vidiet."""
    import woo_mcp.server as srv

    monkeypatch.setenv("WOO_MODE", "store")
    monkeypatch.setenv("WOO_BASE_URL", "https://example-shop.sk")
    monkeypatch.setattr(srv, "_klient", None)

    rodic = store_produkt(4016, typ="variable", varianty=[{"id": 4025}],
                          obrazky=[{"id": 1, "src": "x", "alt": ""}])

    def falosny_get(url, params=None, **kw):
        if url.endswith("/products/4025"):
            return FalosnaOdpoved(store_produkt(
                4025, obrazky=[{"id": 2, "src": "x", "alt": ""},
                               {"id": 3, "src": "x", "alt": ""}]))
        return FalosnaOdpoved([rodic])

    monkeypatch.setattr(httpx, "get", falosny_get)

    vysledok = await srv.mcp.call_tool("audit_seo", {"limit": 10})
    data = json.loads(vysledok.content[0].text)

    assert data["skontrolovanych_produktov"] == 1
    assert data["skontrolovanych_variantov"] == 1
    assert data["obrazkov_spolu"] == 3, "1 rodicovsky + 2 z varianty"
    assert data["obrazkov_bez_alt_textu"] == 3
    monkeypatch.setattr(srv, "_klient", None)


async def test_audit_bez_variantov_ich_prizna(monkeypatch):
    import woo_mcp.server as srv

    monkeypatch.setenv("WOO_MODE", "store")
    monkeypatch.setenv("WOO_BASE_URL", "https://example-shop.sk")
    monkeypatch.setattr(srv, "_klient", None)
    monkeypatch.setattr(httpx, "get", lambda url, params=None, **kw: FalosnaOdpoved(
        [store_produkt(4016, typ="variable", varianty=[{"id": 4025}])]))

    vysledok = await srv.mcp.call_tool(
        "audit_seo", {"limit": 10, "zahrn_varianty": False})
    data = json.loads(vysledok.content[0].text)

    assert data["skontrolovanych_variantov"] == 0
    assert "nekontrolovane" in data, "vynechany rozsah sa musi priznat"
    monkeypatch.setattr(srv, "_klient", None)


# --- alt texty ----------------------------------------------------------


@pytest.fixture
def live_klient(monkeypatch):
    monkeypatch.setenv("WOO_MODE", "live")
    monkeypatch.setenv("WOO_BASE_URL", "https://example-shop.sk")
    monkeypatch.setenv("WOO_CONSUMER_KEY", "ck_test")
    monkeypatch.setenv("WOO_CONSUMER_SECRET", "cs_test")
    return WooClient()


def test_alt_text_posle_celu_galeriu(live_klient, monkeypatch):
    """Toto je cely dovod, preco set_alt_text existuje.

    WooCommerce nahradi galeriu tym, co dostane. Keby sme poslali len menený
    obrazok, produkt by prisiel o zvysne dve fotky.
    """
    produkt = store_produkt(101, obrazky=[
        {"id": 9101, "src": "https://x/a.jpg", "alt": ""},
        {"id": 9102, "src": "https://x/b.jpg", "alt": "Zadny pohlad"},
        {"id": 9103, "src": "https://x/c.jpg", "alt": "Detail uchytenia"},
    ])
    odoslane = {}

    monkeypatch.setattr(httpx, "get", lambda url, **kw: FalosnaOdpoved(produkt))

    def falosny_put(url, json=None, **kw):
        odoslane["telo"] = json
        return FalosnaOdpoved(produkt)

    monkeypatch.setattr(httpx, "put", falosny_put)

    vysledok = live_klient.nastav_alt_texty(101, {"9101": "Predny pohlad"})

    assert vysledok["vykonane"] is True
    poslane_obrazky = odoslane["telo"]["images"]
    assert [o["id"] for o in poslane_obrazky] == [9101, 9102, 9103], \
        "musia sa poslat vsetky obrazky, inak WooCommerce zvysok zmaze"
    assert poslane_obrazky[0]["alt"] == "Predny pohlad"
    assert poslane_obrazky[1]["alt"] == "Zadny pohlad", "cudzi alt sa nesmie stratit"
    assert poslane_obrazky[2]["alt"] == "Detail uchytenia"


def test_alt_text_bez_zmeny_nezapisuje(live_klient, monkeypatch):
    """Zbytocny PUT na produkt je zbytocne riziko - nesmie odist."""
    produkt = store_produkt(101, obrazky=[
        {"id": 9101, "src": "https://x/a.jpg", "alt": "Predny pohlad"},
    ])
    monkeypatch.setattr(httpx, "get", lambda url, **kw: FalosnaOdpoved(produkt))

    def nesmie_sa_zavolat(*a, **kw):
        raise AssertionError("PUT sa nemal poslat, alt text je uz spravny")

    monkeypatch.setattr(httpx, "put", nesmie_sa_zavolat)

    vysledok = live_klient.nastav_alt_texty(101, {"9101": "Predny pohlad"})
    assert vysledok["vykonane"] is False
    assert vysledok["nahlad_zmien"] == {}


def test_alt_text_v_store_rezime_zlyha(store_klient, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: FalosnaOdpoved(store_produkt(1)))
    with pytest.raises(WooChyba, match="iba na citanie"):
        store_klient.nastav_alt_texty(1, {"901": "Alt"})


def test_prazdny_html_popis_je_chybajuci_popis():
    from woo_mcp.server import _bez_html
    assert _bez_html("<p></p>") == ""
    assert _bez_html("<p>&nbsp;</p>") == ""
    assert _bez_html("<p>Skutocny popis.</p>") == "Skutocny popis."
