# Kontrolný zoznam pred spustením e-shopu

| # | Položka | Kde musí byť | Časté chyby |
|---|---|---|---|
| 1 | Obchodné podmienky | odkaz v pätičke + zaškrtávacie pole v košíku | odkaz na zrušený zákon 102/2014 |
| 2 | Reklamačný poriadok | pätička, dostupný pred objednaním | býva len v e-maile po objednávke |
| 3 | Zásady ochrany osobných údajov | pätička + pri každom formulári | chýba pri kontaktnom formulári |
| 4 | Zásady používania cookies | pätička + cookie lišta | lišta bez možnosti odmietnuť |
| 5 | Formulár na odstúpenie od zmluvy | stiahnuteľný súbor + súčasť potvrdenia objednávky | iba spomenutý, neposkytnutý |
| 6 | Identifikačné údaje predávajúceho | pätička alebo stránka Kontakt | chýba IČO/DIČ alebo adresa sídla |
| 7 | Informácia o orgáne dozoru (SOI) | obchodné podmienky | chýba úplne |
| 8 | Odkaz na platformu RSO | obchodné podmienky | chýba úplne |
| 9 | Cena vrátane DPH | pri každom produkte | cena bez DPH bez upozornenia |
| 10 | Cena dopravy pred záväznou objednávkou | košík, nie až posledný krok | zobrazí sa až po zadaní adresy |
| 11 | Zaškrtávacie pole súhlasu | nesmie byť predvyplnené | plugin ho predvolene zaškrtne |
| 12 | Potvrdenie objednávky e-mailom | automaticky | šablóna neobsahuje obchodné podmienky |

## Ako to kontrolovať

Prejdi celý nákup ako zákazník, nie ako admin — vrátane platby v testovacom režime.
Polovica nálezov sa ukáže až v skutočnom procese objednávky.

Cookie lištu kontroluj v prehliadači v anonymnom okne so záložkou Network: ak sa
skript Google Analytics načíta ešte pred kliknutím na „Súhlasím", súhlas je len
kozmetický.
