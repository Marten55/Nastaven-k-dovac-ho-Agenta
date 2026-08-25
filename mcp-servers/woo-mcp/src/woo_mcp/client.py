"""Klient nad WooCommerce REST API s tromi rezimami prevadzky.

fixtures - offline, cita JSON z fixtures/. Ziadna siet, bezpecne na demo a testy.
dry-run  - citanie ide naozivo, zapisy sa NEVYKONAJU, vrati sa nahlad zmeny.
live     - plny zapis.

Rezim sa berie z premennej WOO_MODE. Default je fixtures, teda najbezpecnejsia
moznost - server sa nikdy nespusti omylom v zapisovom rezime.
"""
from __future__ import annotations

import json
import os
import pathlib
from typing import Any

import httpx

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "fixtures"

PLATNE_REZIMY = ("fixtures", "dry-run", "live")


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

        if self.mode != "fixtures" and not (self.base_url and self.key and self.secret):
            raise WooChyba(
                f"Rezim '{self.mode}' potrebuje WOO_BASE_URL, WOO_CONSUMER_KEY a "
                "WOO_CONSUMER_SECRET. Skopiruj .env.example na .env a doplo ich, "
                "alebo prepni WOO_MODE=fixtures."
            )

    # --- pomocne ---------------------------------------------------------

    @property
    def zapis_povoleny(self) -> bool:
        return self.mode == "live"

    def maskovana_domena(self) -> str:
        if not self.base_url:
            return "(nenastavene - rezim fixtures)"
        return self.base_url

    def _fixture(self, nazov: str) -> list[dict[str, Any]]:
        cesta = FIXTURES / f"{nazov}.json"
        if not cesta.exists():
            raise WooChyba(f"Chyba fixture subor {cesta.name} v {FIXTURES}.")
        return json.loads(cesta.read_text(encoding="utf-8"))

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/wp-json/wc/v3/{endpoint}"
        try:
            odpoved = httpx.get(
                url,
                params=params or {},
                auth=(self.key, self.secret),
                timeout=30.0,
                follow_redirects=True,
            )
        except httpx.HTTPError as chyba:
            raise WooChyba(f"Nepodarilo sa spojit s {self.base_url}: {chyba}") from chyba

        if odpoved.status_code == 401:
            raise WooChyba(
                "401 Unauthorized. Najcastejsia pricina na WooCommerce: kluce sa "
                "posielaju cez HTTP Basic, ktory funguje len cez HTTPS, alebo ma "
                "kluc len opravnenie 'Citanie'. Skontroluj oboje."
            )
        if odpoved.status_code >= 400:
            raise WooChyba(f"WooCommerce vratil {odpoved.status_code}: {odpoved.text[:300]}")
        return odpoved.json()

    # --- citanie ---------------------------------------------------------

    def produkty(self, hladaj: str = "", limit: int = 20) -> list[dict[str, Any]]:
        if self.mode == "fixtures":
            data = self._fixture("products")
            if hladaj:
                h = hladaj.lower()
                data = [
                    p for p in data
                    if h in p.get("name", "").lower() or h in p.get("sku", "").lower()
                ]
            return data[:limit]
        return self._get("products", {"search": hladaj, "per_page": limit})

    def produkt(self, identifikator: str) -> dict[str, Any] | None:
        if self.mode == "fixtures":
            for p in self._fixture("products"):
                if str(p.get("id")) == str(identifikator) or p.get("sku") == identifikator:
                    return p
            return None
        if str(identifikator).isdigit():
            return self._get(f"products/{identifikator}")
        vysledok = self._get("products", {"sku": identifikator})
        return vysledok[0] if vysledok else None

    def objednavky(self, stav: str = "any", limit: int = 20) -> list[dict[str, Any]]:
        if self.mode == "fixtures":
            data = self._fixture("orders")
            if stav != "any":
                data = [o for o in data if o.get("status") == stav]
            return data[:limit]
        return self._get("orders", {"status": stav, "per_page": limit})

    # --- zapis -----------------------------------------------------------

    def uprav_produkt(self, product_id: int, zmeny: dict[str, Any]) -> dict[str, Any]:
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
                    "Zmena sa NEZAPISALA. Rezim je "
                    f"'{self.mode}'. Na skutocny zapis nastav WOO_MODE=live."
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
