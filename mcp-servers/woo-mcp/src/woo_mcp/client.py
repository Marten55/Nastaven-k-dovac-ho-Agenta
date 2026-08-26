"""Klient nad WooCommerce s viacerymi rezimami prevadzky.

fixtures - offline, cita JSON z fixtures/. Ziadna siet, bezpecne na demo a testy.
store    - verejne Store API, iba citanie, BEZ prihlasovacich udajov.
dry-run  - wc/v3 naozivo, zapisy sa NEVYKONAJU, vrati sa nahlad zmeny.
live     - wc/v3, plny zapis.

Rezim sa berie z premennej WOO_MODE. Default je fixtures, teda najbezpecnejsia
moznost - server sa nikdy nespusti omylom v zapisovom rezime.

Rezim `store` je tu preto, ze audit e-shopu casto treba spravit skor, nez klient
vygeneruje API kluce. Store API vracia to iste, co vidi navstevnik: nazov, SKU,
kratky popis, kategorie a obrazky vratane alt textov.
"""
from __future__ import annotations

import json
import os
import pathlib
from typing import Any

import httpx

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "fixtures"

PLATNE_REZIMY = ("fixtures", "store", "dry-run", "live")

# WooCommerce zastropuje per_page na 100 bez ohladu na to, co posles.
MAX_PER_PAGE = 100
# Poistka proti nekonecnemu strankovaniu pri chybnej odpovedi servera.
MAX_STRAN = 20


class WooChyba(RuntimeError):
    """Zrozumitelna chyba, ktora sa da vratit modelu ako text."""


class WooClient:
    def __init__(self) -> None:
        self.mode = (os.environ.get("WOO_MODE") or "fixtures").strip().lower()
        if self.mode not in PLATNE_REZIMY:
            raise WooChyba(
                f"Neznamy WOO_MODE={self.mode!r}. Povolene: {', '.join(PLATNE_REZIMY)}."
            )
        self.base_url = (os.environ.get("WOO_BASE_URL") or "").rstrip("/")
        self.key = os.environ.get("WOO_CONSUMER_KEY") or ""
        self.secret = os.environ.get("WOO_CONSUMER_SECRET") or ""

        if self.mode == "store" and not self.base_url:
            raise WooChyba(
                "Rezim 'store' potrebuje WOO_BASE_URL. Kluce netreba - Store API je "
                "verejne. Nastav napr. WOO_BASE_URL=https://example-shop.sk."
            )
        if self.mode in ("dry-run", "live") and not (self.base_url and self.key and self.secret):
            raise WooChyba(
                f"Rezim '{self.mode}' potrebuje WOO_BASE_URL, WOO_CONSUMER_KEY a "
                "WOO_CONSUMER_SECRET. Skopiruj .env.example na .env a doplo ich, "
                "alebo pouzi WOO_MODE=store (iba citanie, bez klucov)."
            )

    # --- vlastnosti rezimu ----------------------------------------------

    @property
    def zapis_povoleny(self) -> bool:
        return self.mode == "live"

    @property
    def cita_naozivo(self) -> bool:
        return self.mode in ("store", "dry-run", "live")

    def maskovana_domena(self) -> str:
        return self.base_url or "(nenastavene - rezim fixtures)"

    # --- HTTP ------------------------------------------------------------

    def _ziadost(self, url: str, params: dict[str, Any], s_autentifikaciou: bool) -> Any:
        try:
            odpoved = httpx.get(
                url,
                params=params,
                auth=(self.key, self.secret) if s_autentifikaciou else None,
                timeout=30.0,
                follow_redirects=True,
            )
        except httpx.HTTPError as chyba:
            raise WooChyba(f"Nepodarilo sa spojit s {self.base_url}: {chyba}") from chyba

        if odpoved.status_code == 401:
            raise WooChyba(
                "401 Unauthorized. Na WooCommerce to byva tym, ze kluce chodia cez "
                "HTTP Basic, ktory funguje len cez HTTPS, alebo ze kluc ma len "
                "opravnenie 'Citanie'. Na samotny audit staci WOO_MODE=store, "
                "ktory kluce nepotrebuje."
            )
        if odpoved.status_code >= 400:
            raise WooChyba(f"E-shop vratil {odpoved.status_code}: {odpoved.text[:300]}")
        return odpoved.json()

    def _v3(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self._ziadost(
            f"{self.base_url}/wp-json/wc/v3/{endpoint}", params or {}, True
        )

    def _store(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self._ziadost(
            f"{self.base_url}/wp-json/wc/store/v1/{endpoint}", params or {}, False
        )

    def _vsetky_stranky(self, endpoint: str, params: dict[str, Any],
                        limit: int) -> tuple[list, bool]:
        """Prejde strankovanie az po `limit` poloziek.

        WooCommerce vracia najviac 100 poloziek na poziadavku bez ohladu na to,
        co posles. Bez tohto by sa pri katalogu nad 100 produktov ticho vynechal
        zvysok a audit by hlasil menej nalezov, nez ich naozaj je.

        Vracia (polozky, neuplne). `neuplne` je True, ked sa narazilo na poistku
        MAX_STRAN - vysledok je vtedy orezany a nesmie sa prezentovat ako uplny.
        """
        zozbierane: list[Any] = []
        strana = 1
        while len(zozbierane) < limit and strana <= MAX_STRAN:
            kolko = min(MAX_PER_PAGE, limit - len(zozbierane))
            davka = (self._store if self.mode == "store" else self._v3)(
                endpoint, {**params, "per_page": kolko, "page": strana}
            )
            if not isinstance(davka, list) or not davka:
                return zozbierane, False
            zozbierane.extend(davka)
            if len(davka) < kolko:
                return zozbierane, False
            strana += 1
        return zozbierane[:limit], strana > MAX_STRAN

    # --- normalizacia ----------------------------------------------------

    @staticmethod
    def _zo_store(p: dict[str, Any]) -> dict[str, Any]:
        """Store API ma iny tvar nez wc/v3. Zjednotime ho, nech zvysok kodu
        nemusi vediet, z ktoreho rozhrania data prisli."""
        ceny = p.get("prices") or {}
        cena = ceny.get("price")
        jednotky = ceny.get("currency_minor_unit")
        if cena is not None and isinstance(jednotky, int):
            try:
                cena = f"{int(cena) / (10 ** jednotky):.2f}"
            except (TypeError, ValueError):
                cena = str(cena)

        if p.get("is_in_stock") is False:
            stav = "outofstock"
        elif p.get("on_backorder"):
            stav = "onbackorder"
        else:
            stav = "instock"

        return {
            "id": p.get("id"),
            "sku": p.get("sku", ""),
            "name": p.get("name", ""),
            "price": cena,
            "stock_status": stav,
            "stock_quantity": None,
            "backorders": "notify" if p.get("on_backorder") else "no",
            "categories": p.get("categories", []),
            "short_description": p.get("short_description", ""),
            "description": p.get("description", ""),
            "images": [
                {"id": o.get("id"), "src": o.get("src", ""), "alt": o.get("alt", "")}
                for o in p.get("images", [])
            ],
            "type": p.get("type", "simple"),
            "variations": [v.get("id") for v in p.get("variations", []) if v.get("id")],
        }

    @staticmethod
    def _zo_v3(p: dict[str, Any]) -> dict[str, Any]:
        p = dict(p)
        p.setdefault("type", "simple")
        p.setdefault("variations", [])
        return p

    def _normalizuj(self, p: dict[str, Any]) -> dict[str, Any]:
        return self._zo_store(p) if self.mode == "store" else self._zo_v3(p)

    # --- citanie ---------------------------------------------------------

    def produkty(self, hladaj: str = "", limit: int = 20) -> tuple[list[dict[str, Any]], bool]:
        if self.mode == "fixtures":
            data = json.loads((FIXTURES / "products.json").read_text(encoding="utf-8"))
            if hladaj:
                h = hladaj.lower()
                data = [p for p in data
                        if h in p.get("name", "").lower() or h in p.get("sku", "").lower()]
            return [self._zo_v3(p) for p in data[:limit]], False

        params: dict[str, Any] = {"search": hladaj} if hladaj else {}
        if self.mode != "store":
            # Bez tohto vracia wc/v3 aj produkty v kosi a v koncepte.
            params["status"] = "publish"

        surove, neuplne = self._vsetky_stranky("products", params, limit)
        return [self._normalizuj(p) for p in surove], neuplne

    def produkt(self, identifikator: str) -> dict[str, Any] | None:
        if self.mode == "fixtures":
            data = json.loads((FIXTURES / "products.json").read_text(encoding="utf-8"))
            for p in data:
                if str(p.get("id")) == str(identifikator) or p.get("sku") == identifikator:
                    return self._zo_v3(p)
            return None

        if str(identifikator).isdigit():
            koncovka = f"products/{identifikator}"
            try:
                return self._normalizuj(
                    self._store(koncovka) if self.mode == "store" else self._v3(koncovka)
                )
            except WooChyba:
                return None

        najdene, _ = self.produkty(identifikator, 20)
        for p in najdene:
            if p.get("sku") == identifikator:
                return p
        return None

    def varianty(self, produkt: dict[str, Any]) -> list[dict[str, Any]]:
        """Nacita varianty variabilneho produktu aj s ich vlastnymi obrazkami.

        Variant ma vlastnu fotku, ktora sa zobrazi po prepnuti farby. Audit,
        ktory pozera len na rodicovsky produkt, tieto fotky nikdy neuvidi.
        """
        if produkt.get("type") != "variable":
            return []
        vysledok = []
        for vid in produkt.get("variations", [])[:20]:
            v = self.produkt(str(vid))
            if v:
                vysledok.append(v)
        return vysledok

    def objednavky(self, stav: str = "any", limit: int = 20) -> list[dict[str, Any]]:
        if self.mode == "fixtures":
            data = json.loads((FIXTURES / "orders.json").read_text(encoding="utf-8"))
            if stav != "any":
                data = [o for o in data if o.get("status") == stav]
            return data[:limit]
        if self.mode == "store":
            raise WooChyba(
                "Objednavky cez verejne Store API nie su dostupne - to by bola "
                "bezpecnostna diera. Pouzi WOO_MODE=dry-run alebo live s klucmi."
            )
        polozky, _ = self._vsetky_stranky("orders", {"status": stav}, limit)
        return polozky

    # --- zapis -----------------------------------------------------------

    def uprav_produkt(self, product_id: int, zmeny: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "store":
            raise WooChyba(
                "Rezim 'store' je iba na citanie - Store API zapis neumoznuje. "
                "Na zapis pouzi WOO_MODE=live s API klucmi."
            )

        povodny = self.produkt(str(product_id))
        if povodny is None:
            raise WooChyba(f"Produkt {product_id} neexistuje.")

        nahlad = {
            pole: {"predtym": povodny.get(pole), "potom": hodnota}
            for pole, hodnota in zmeny.items()
        }

        if not self.zapis_povoleny:
            return {
                "vykonane": False,
                "rezim": self.mode,
                "product_id": product_id,
                "nahlad_zmien": nahlad,
                "poznamka": (
                    f"Zmena sa NEZAPISALA. Rezim je '{self.mode}'. "
                    "Na skutocny zapis nastav WOO_MODE=live."
                ),
            }

        url = f"{self.base_url}/wp-json/wc/v3/products/{product_id}"
        try:
            odpoved = httpx.put(
                url, json=zmeny, auth=(self.key, self.secret),
                timeout=30.0, follow_redirects=True,
            )
        except httpx.HTTPError as chyba:
            raise WooChyba(f"Zapis zlyhal: {chyba}") from chyba
        if odpoved.status_code >= 400:
            raise WooChyba(f"WooCommerce vratil {odpoved.status_code}: {odpoved.text[:300]}")

        return {
            "vykonane": True,
            "rezim": self.mode,
            "product_id": product_id,
            "nahlad_zmien": nahlad,
        }
