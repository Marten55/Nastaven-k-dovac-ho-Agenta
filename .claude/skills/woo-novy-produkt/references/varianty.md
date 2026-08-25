# Zlučovanie produktov do variantov

Postup je nezvratný. Rob ho iba po výslovnom odsúhlasení klientom.

## Predtým ako začneš

1. Export produktov do CSV ako záloha (WooCommerce → Produkty → Exportovať).
2. Zoznam URL adries, ktoré zaniknú — budú treba presmerovania.
3. Over, či na rušené produkty nevedú odkazy z Google Merchant / Heureka feedu.

## Kroky

1. Vytvor **variabilný** produkt (typ `variable`), nie jednoduchý.
2. Založ atribút (napr. „Veľkosť", „Farba"), zaškrtni **Použiť na varianty**.
3. Vygeneruj varianty a doplň im SKU, cenu a sklad jednotlivo — hromadná akcia
   „nastaviť cenu" prepíše aj varianty, kde bola cena zámerne iná.
4. Fotky: hlavná fotka patrí rodičovi, fotka konkrétnej varianty sa nastavuje
   v riadku varianty. Bez toho sa po prepnutí varianty obrázok nemení.
5. Pôvodné samostatné produkty **nemaž** — prepni ich na koncept, kým nefunguje
   presmerovanie.
6. Nastav 301 presmerovania zo starých URL na nový variabilný produkt.
7. Až potom staré produkty zmaž.

## Časté problémy

- **Varianta sa nedá vybrať** — atribút nemá zaškrtnuté „Použiť na varianty".
- **Cena sa zobrazuje ako rozsah** — je to správanie WooCommerce; ak to klientovi
  prekáža, rieši sa to filtrom `woocommerce_variable_price_html` v child téme,
  nie úpravou pluginu.
- **Sklad sa neodpočítava** — správa skladu musí byť zapnutá na úrovni varianty,
  nie iba na rodičovi.
- **Zmizli recenzie** — recenzie sú viazané na ID pôvodného produktu a pri zlúčení
  sa nepresúvajú. Ak sú dôležité, prenes ich pred zmazaním.
