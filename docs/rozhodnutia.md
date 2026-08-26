# Denník rozhodnutí

Prečo je setup postavený takto a čo bola alternatíva.

## 1. Vlastné repo namiesto exportu existujúcej konfigurácie

**Rozhodnutie:** postaviť setup od nuly ako samostatné repo.

**Prečo:** pôvodná konfigurácia bola celá v pluginoch z verejného marketplace —
`~/.claude/agents/`, `skills/` aj `commands/` boli prázdne. Zadanie pluginy aj
marketplace zakazuje, takže export by neodovzdal nič vlastné.

**Dôsledok:** všetko v repe je písané pre tento setup. Nič nie je prevzaté z pluginu.

## 2. Doména e-shopov namiesto generického dema

**Rozhodnutie:** postaviť setup na WooCommerce práci pre slovenských klientov.

**Prečo:** skill má hodnotu len vtedy, keď obsahuje znalosť, ktorú model nemá alebo
si ju musí prácne odvodzovať. Generický „code review" skill je prepis dokumentácie.
Naopak `$e.run` namiesto drag & drop, dvojfázové nastavenie alt textu vo WP REST
alebo to, že 102/2014 je zrušený zákon, sú veci overené praxou.

**Alternatíva:** postaviť to na leadgene, kde MCP server už existoval. Ušetrilo by to
čas na písaní servera, ale odovzdal by sa hotový kód namiesto nového.

## 3. Odstupňované režimy MCP servera namiesto jedného

**Rozhodnutie:** pôvodne `fixtures` / `dry-run` / `live`, default `fixtures`.
Štvrtý režim `store` pribudol neskôr, viď bod 7.

**Prečo:** setup pracuje s e-shopmi, z ktorých klienti žijú. Server, ktorý sa
predvolene spustí v zápisovom režime, je otázka času do prvej nehody. Zároveň to
rieši praktický problém odovzdávky: hodnotiteľ si repo naklonuje a všetko funguje
bez prístupu k akémukoľvek e-shopu.

**Cena:** o niečo viac kódu v klientovi a nutnosť režim všade hlásiť.

## 4. Zápis je v `permissions.ask`, nie v `allow`

**Rozhodnutie:** čítacie MCP nástroje sú predschválené, `update_product`
a `set_alt_text` si vždy pýtajú potvrdenie.

**Prečo:** predschválené čítanie odstráni väčšinu vyskakovacích potvrdení, takže
používateľ prestane klikať „povoliť" automaticky. Potvrdenie potom niečo znamená.

## 5. Hook namiesto ďalšej vety v CLAUDE.md

**Rozhodnutie:** zákaz zápisu do jadra WordPressu je vynútený skriptom.

**Prečo:** inštrukcia v `CLAUDE.md` je text, ktorý sa dá prehliadnuť pri dlhej relácii.
`guard_wp_core.py` beží pred každým `Write`/`Edit` a vráti zamietnutie s návodom, kam
zmena patrí. Má vlastné testy, takže sa vie, že naozaj funguje.

**Cena:** hook musí poznať výnimky (child téma, vlastné ADM pluginy), inak by
blokoval aj legitímnu prácu. Preto tých 10 testovacích prípadov.

## 6. Rôzne modely pre rôznych subagentov

**Rozhodnutie:** `haiku` pre `php-reviewer`, `sonnet` pre editora a copywritera,
`opus` pre audítora.

**Prečo:** kontrola snippetu proti zoznamu vzorov je mechanická práca. Audit, kde
treba zoradiť nálezy podľa dopadu na klienta, nie je. Platiť za opus v oboch
prípadoch je zbytočné.

## 7. Štvrtý režim `store` a čo ho vyvolalo

**Rozhodnutie:** pridať režim `store` — čítanie cez verejné WooCommerce Store API,
bez prihlasovacích údajov.

**Prečo:** pri prvom nasadení na reálny e-shop sa ukázalo, že pôvodné tri režimy
nestačia. Audit treba spraviť najčastejšie skôr, než klient vôbec vygeneruje API
kľúče. Store API je verejné, vracia názov, SKU, krátky popis, kategórie aj alt texty
obrázkov, a zápis cezeň nejde — takže sa v tomto režime nedá nič pokaziť.

**Cena:** Store API má iný tvar odpovede než wc/v3 (ceny v centoch, popisy ako HTML,
iná štruktúra skladu), takže pribudla normalizačná vrstva. Bez nej by každý nástroj
musel vedieť, z ktorého rozhrania dáta prišli.

## 8. Dve ticho nesprávne odpovede, ktoré nasadenie odhalilo

Prvé použitie na katalógu so 127 produktmi ukázalo dve chyby, ktoré nepadali —
len vracali menšie čísla, než je pravda. To je horší druh chyby než výnimka.

1. **Stránkovanie.** WooCommerce zastropuje `per_page` na 100 bez ohľadu na to, čo
   pošleš. Audit teda prešiel prvých 100 produktov a zvyšok ticho vynechal.
2. **Varianty.** Fotka varianty sa na e-shope zobrazí až po prepnutí farby a visí na
   samostatnom objekte. Audit, ktorý pozeral len na rodičovský produkt, ich nevidel —
   na reálnom katalógu išlo o 102 obrázkov navyše.

**Dôsledok pre návrh:** kdekoľvek sa výsledok oreže, vracia sa pole `upozornenie`
a vypnutý rozsah sa hlási v poli `nekontrolovane`. Nástroj, ktorý zamlčí, čo nevidel,
je nebezpečnejší než nástroj, ktorý zlyhá nahlas.

## 9. Čo sa do setupu zámerne nedostalo

| Vec | Prečo nie |
|---|---|
| MCP server na Gmail/Notion | v repe by boli osobné prístupy klienta |
| Automatické commitovanie a push | agent nemá tlačiť na klientske repo bez kontroly |
| Skill na dizajn a grafiku | nesúvisí s doménou tohto setupu, bola by to vata |
| `tools: *` u ktoréhokoľvek subagenta | zmazalo by to celý zmysel izolácie |
