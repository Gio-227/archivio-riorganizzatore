# Verifica (Fase 4)

Verifica che la riorganizzazione sia completa e corretta prima del backup su disco esterno.
**Diff su cache, non ri-scan.** Due strumenti standard, in quest'ordine: **widget di verifica**
(quantitativo, v1.2.1) e **debrief albero** (qualitativo, umano).

## 1 · Widget di verifica — `assets/widget_verifica_template.html`

Popola il template con i dati del diff cache↔disco (+ eventuale riconciliazione con un backup
di riferimento, quando esiste). Salva come `[NomeProgetto]_verifica.html`. Tre classi, mutuamente
esclusive, che devono sommare al totale:

- **Congruenze** — file vivi: identici al loro posto, ricollocati (dove), rinominati, modificati.
- **Incongruenze volute** — eliminazioni/merge deliberati: ogni riga con badge canonico e
  **fonte documentale** (decisione + esecuzione: widget/report + script/journal). Senza fonte,
  la riga non è "voluta": va sotto.
- **Mismatch imprevisti** — tutto ciò che non torna. Se recuperabile (backup, Cestino): recupera
  PRIMA di chiudere la verifica, poi marca risolto. Diventa lezione nel report.

Più due blocchi di sintesi: **recap rinomine** (esempi prima→dopo + la grammatica adottata,
es. `AAAA-MM-GG_cosa.ext`) e **logica layout** (albero finale + regole della tassonomia applicata).
Regole d'oro: quadratura dichiarata (i conteggi devono sommare, per ramo); percorsi sempre
**assoluti e completi**; pagina **statica** — nessuna azione parte dal widget; iniettare i dati
nel template, MAI riscrivere CSS/JS (anti-deriva, cfr. `docs/REGOLE_WIDGET.md`).

Metodo di riconciliazione consigliato (quando c'è un riferimento da quadrare): match **multiset
nome+size** → i residui per (size+ext) = rinominati probabili → poi solo-nome = modificati →
il resto va spiegato con le fonti o dichiarato imprevisto.

## 2 · Debrief albero (OBBLIGATORIO — chiude ogni riorg)

```powershell
scripts\albero.ps1 -Target "<cartella riorganizzata>" -Out "<...>\_riorg\<data>_albero.html" -Title "<area>"
```

Oppure, su ogni sistema (v1.3-beta, stesso HTML, pre-flight `ax` incorporato):

```
python3 scripts/riorg.py albero --target "<cartella riorganizzata>" --out "<...>/<data>_albero.html" --title "<area>"
python3 scripts/riorg.py albero --check "<albero.html>"   # controlla anche HTML prodotti altrove
```

`riorg.py albero` nasconde la spazzatura di sistema (`.DS_Store`, `._*`…); `--show-junk` la mostra.

Albero completo navigabile (chevron, Espandi/Collassa, conteggio figli), **commento per ogni
riga** con tag **Nota / Sposta / Ripristina / Elimina**, **Esporta risposte** (`[tag] percorso —
commento`, Copia + Scarica .md). È la verifica umana finale: l'utente annota, tu esegui **solo**
le correzioni marcate, usando il journal per i ripristini (`undo.ps1 -Journal <run>`).
Genera l'albero **dal sistema che ha eseguito** (su Windows: PowerShell o `riorg.py` nativo; il mount
bash può essere stantio dopo gli spostamenti). NB: i commenti sono keyed per path in localStorage → dopo nuovi spostamenti
diventano stale nell'export.

## Verifica dal disco (v1.3-beta)

Prima del widget: MD5 (o dimensione) delle destinazioni contro le sorgenti, sorgenti sparite dove
dovevano sparire, contenuto della quarantena, e **copie di riferimento dei doppioni ancora al loro
posto**. Lo stato si rilegge dal disco, non dal messaggio di successo. Se il sistema è nuovo per la
skill, chiudi con il feedback di `references/5_benchmark.md`.

## Cosa segnalare sempre

- File attesi mancanti o fuori posto · VERIFICA ancora aperti (confidence <0.50, PDF scansionati).
- Delta conteggio/dimensioni vs atteso, spiegato voce per voce.
- Il disco esterno resta **intoccato** finché la verifica non è approvata dall'utente.
