---
name: "archivio-riorganizzatore"
description: "Usa questa skill quando l'utente vuole riorganizzare, pulire, ristrutturare o archiviare una cartella di file sul filesystem del suo PC. Trigger: \"riorganizza questa cartella\", \"metti ordine in\", \"archivia i file di\", \"struttura l'archivio di\", \"pulisci la cartella\", \"trova i doppioni in\", \"ho una cartella piena di file\", \"devo mettere ordine nel desktop\". Proattiva su cartelle con molti file, nomi incoerenti, doppioni o contenuto misto. Anche per catalogare foto/video (marchio, progetti video), raggruppare atti amministrativi per area, categorizzare fatture per analisi gestionale. NON usare per: pulizia cache/sistema/spazio disco; archiviazione di chat o conversazioni; dedup dentro file dati (CSV/rubriche); riordino scheduled task o sessioni Cowork (vedi ripulizia-cognitiva); operazioni atomiche su singolo file; interni di applicazioni o progetti di codice; domande informative su dimensioni. Verbi vincolati a \"cartella di file sul filesystem\"."
---

# Skill: Archivio Riorganizzatore — v1.3-beta

**v1.3-beta — due sistemi operativi, un solo flusso (30/09/2026).** La skill riconosce dove gira
(`scripts/riorg.py env`) e sceglie il motore: **PowerShell** (`*.ps1`, collaudato su Windows) oppure
**`riorg.py`** (Python, solo libreria standard: Windows, macOS, Linux). Tre cambi di sostanza:
(1) **ELIMINA = quarantena** su tutti i sistemi — il file va in `_DA_ELIMINARE\<run_id>\` sullo stesso
volume e torna indietro con l'undo; il Cestino resta solo opt-in su dischi locali fissi, perché
**sulle unità di rete e rimovibili il Cestino non esiste** e l'eliminazione sarebbe definitiva;
(2) **nuova op COPIA** (ripresa senza ricopiare, verifica dimensione o MD5) per le «cartelle uniche»
che non toccano gli originali; (3) **metriche e autocontrollo in ogni comando** (`riorg_metrics.jsonl`)
e un **bench** su cartella sintetica per confrontare sistemi e versioni. Collaudo: bench 17/17 su
Linux e Windows (30/09/2026); **macOS non ancora collaudato → beta**. Numeri in `references/5_benchmark.md`.

Riorganizza, deduplica e archivia una cartella disordinata con flusso a 5 fasi
**Interroga → Mappa → Proponi → Esegui → Verifica**, reversibile e human-in-the-loop. La v1.1 taglia il
costo token con 5 leve (cache anti-rilettura, script in `scripts/`, briefing progressivo,
confidence gate, undo journal) senza toccare la qualità dell'output (8 classi anomalie, op
proposte, dedup invariati).

**v1.2 — due aggiunte:** (1) il widget di proposta mostra il layout cartelle **attuale → proposto**
con un **albero interattivo** (icone, chevron cliccabili, nodi che cambiano in verde) al posto dell'ASCII;
(2) **debrief albero obbligatorio** a fine flusso — albero completo navigabile, **commento per ogni riga**
ed **Esporta risposte**, per correzioni e ripristini puntuali dopo la verifica dell'utente.

**v1.2.1 — sicurezza + verifica standard (8 fix):** undo con inverse **strutturate** eseguite da
cmdlet diretti — eliminato `Invoke-Expression` (P0: i path con apostrofo rompevano l'inversa in
silenzio); inversa CREA solo su cartella **vuota**, mai `-Recurse -Force` cieco (P0); ordinamento
stabile `tipo, seq` (P1); **dry-run validante** — sorgenti esistenti + collisioni destinazione →
WARN (P1); **journal per run** `riorg_undo_<run_id>.json` + copia "ultima run" (P2); conteggio
gruppi dedup con `@()` (P2); `Emit` di albero.ps1 resiliente a directory illeggibili (P3);
**widget di verifica standard** in Fase 4 — `assets/widget_verifica_template.html`: congruenze /
incongruenze volute (con fonte documentale) / mismatch imprevisti + recap rinomine e logica layout.

**v1.2.2 — il generatore dell'albero nasceva rotto: fix di classe (bug #23).** Per tre volte i
pulsanti «Espandi/Collassa» degli alberi generati non hanno funzionato, e le prime due volte il fix
è stato applicato all'HTML già prodotto invece che al generatore: quindi ogni albero nuovo tornava
rotto. **Causa:** `scripts/albero.ps1` definiva `function all(c)` e la invocava da handler inline
(`onclick='all(false)'`). Negli handler inline la catena di scope passa da `document` **prima** che
da `window`, e `document.all` esiste come `HTMLAllCollection` invocabile: la chiamata **riesce sul
bersaglio sbagliato e non fa nulla, senza errore in console**. **Rimedio strutturale, non del caso
singolo: tutte le funzioni chiamate da `onclick` portano il prefisso `ax`** — `axSetAll`, `axtg`,
`axnote`, `axexportC`, `axcopyExp`, `axdlExp`, `axsetTag`, `axsaveNote`, `axdelNote` — così nessun
nome può più collidere con una proprietà di `document`. Vedi §Pre-flight sul generatore dell'albero.

## Parametri dichiarati

- **Confidence gate:** ≥0.85 auto · 0.50–0.85 widget con nota · <0.50 VERIFICA manuale.
  Formula e schema in `references/2a_analisi.md`.
- **Autonomia: modalità "b"** — auto CREA / SPOSTA / RINOMINA quando confidence ≥0.85;
  **MERGE ed ELIMINA restano sempre a gate** con conferma esplicita. Vedi `references/3_esecuzione.md`.
- **Sistema operativo:** riconosciuto al pre-flight con `python3 scripts/riorg.py env <percorsi>`
  (sistema, strumenti, filesystem e tipo di unità: locale, rete, rimovibile, cartella di VM).
  Decide il motore della Fase 3 — tabella in «Ambiente di esecuzione».
- **Stato per progetto** in `Documents\Claude\Projects\[NomeProgetto]\`:
  `riorg_cache.json`, `riorg_undo.json`, `riorg_vista.json`, `riorg_capabilities.json` (+ report di run). Isolato per progetto.

## Flusso a 5 fasi

### 0 — Interrogazione iniziale (pre-scan, sola lettura)
Erede della regola "Bomba & Cannone": prima il cannone, poi la bomba. **0a** target+permessi
(assente → fermati e chiedi; mai default hardcoded) **+ sistema e motore** (`riorg.py env`: su un
volume di rete o rimovibile il Cestino non c'è; NTFS su Mac è in sola lettura) · **0b** precontesto quantitativo (1–2 call
aggregate ≤40 righe: GB/file per sottocartella, estensioni, pattern naming, log, repo annidati
→ zone protette, cartelle vuote) · **0c** interrogazione qualitativa (natura, logica archivio,
cosa ottimizzare; in headless non blocca: domande differite nel report) · **0d** visione
sistemica (tabella natura → zona → proposta). Gate per le fasi successive. → `references/0_interrogazione.md`

### 1 — Briefing (sola lettura)
3 domande front-load: **target · obiettivo · vincoli intoccabili** (target già confermato in 0a).
Tutto il resto è default dichiarato nel widget, modificabile lì; domande extra solo se lo scan
trova ambiguità reale. → `references/1_briefing.md`

### 2 — Analisi e proposta (sola lettura)
Scan e dedup con **`riorg.py scan` / `riorg.py dedup --partial`** (qualunque sistema con Python ≥3.8;
raccomandato anche su Windows) oppure `scripts/scan.ps1` / `scripts/dedup.ps1` (Windows senza Python).
CSV + aggregato ≤40 righe, MD5 solo sui candidati per dimensione, impronta rapida (1 MB testa+coda)
prima dell'MD5 pieno sui file grandi, file vuoti mai trattati come doppioni. Doppioni **fra più radici** (due NAS, più dischi):
`riorg.py dedup-multi --pair <radice> <stato> --pair … [--only candidati.txt] --partial`. Zone protette
(`.git`, `node_modules`, pacchetti `.fcpbundle`/`.photoslibrary`/`.lrdata`/`.app`…): interni esclusi da
scan e hash, restano segnalati come unità (regola 11); strutture di scheda camera (`DCIM`, `PRIVATE`,
`CLIPS001`…) marcate come blocchi da tenere interi. `riorg.py` scarta anche la spazzatura di sistema
(`.DS_Store`, `._*`, `Thumbs.db`, `@eaDir`, `#recycle`…), che `scan.ps1` invece conta. Poi: **semantica** (dispatcher `2b_semantica.md` classifica
il dominio, instrada ai moduli, rileva app/codice → zona protetta), **capability** (`2c_capability.md`:
instrada a tool esterni se installati, propone install solo se serve, con cache), **confidence gate**,
mappatura sulle due tassonomie, proposta nel widget. La cache `path+mtime+size` salta ri-hash e ri-scan.
→ `references/2a_analisi.md` · `references/2b_semantica.md` (+ `2b_semantica_visivo/_amministrativo/_finanziario`)
· `references/2c_capability.md` · `references/2d_tassonomia.md`

### 3 — Esecuzione
Dry-run obbligatorio prima del reale, con **validazione che blocca**: sorgente assente, destinazione
occupata, due op sulla stessa destinazione, spostamento fra volumi diversi, spazio insufficiente.
- **Windows:** `scripts/execute.ps1` (dry-run di default) — CREA → SPOSTA → RINOMINA → MERGE → FLATTEN →
  ELIMINA; ELIMINA in quarantena con `-QuarantineRoot` (Cestino solo `-DeleteMode Cestino` su disco fisso);
  undo con `scripts/undo.ps1`.
- **Ogni sistema:** `python3 scripts/riorg.py execute --ops ops.json --state <dir> [--quarantine-root R] [--real]`
  — CREA → COPIA → SPOSTA → RINOMINA → ELIMINA(quarantena); MERGE e FLATTEN non disponibili in beta
  (spezzali in SPOSTA o usa `execute.ps1`); undo con `riorg.py undo [--real]`.
Ogni op entra nel journal *prima* di agire (le cartelle create automaticamente comprese), l'undo
riavvolge in ordine LIFO e rimuove solo cartelle tornate vuote. Esegui **fuori dal mount Cowork**
(vedi "Ambiente di esecuzione"). → `references/3_esecuzione.md`

### 4 — Verifica: WIDGET + DEBRIEF ALBERO
Diff cache↔disco (**non** ri-scan), poi **widget di verifica standard** (v1.2.1,
`assets/widget_verifica_template.html`): tre classi che sommano al totale — **congruenze**
(vivi: identici/ricollocati/rinominati/modificati) · **incongruenze volute** (ogni eliminazione
con badge e **fonte documentale**) · **mismatch imprevisti** (recuperare prima di chiudere) —
più recap rinomine e logica layout. Gate prima del backup su disco esterno. **Poi, sempre:
debrief albero** — `scripts/albero.ps1` (Windows) o `riorg.py albero` (ogni sistema, stesso HTML, pre-flight
incorporato) genera l'albero completo della cartella riorganizzata
(annidamenti aperti, chevron cliccabili, **commento per riga** con tag Nota/Sposta/Ripristina/Elimina
e bottone **Esporta risposte**) e lo presenti all'utente. **Prima di lanciarlo, applica il pre-flight
qui sotto.** Le risposte esportate rientrano come correzioni/ripristini parziali. → `references/4_verifica.md`

## Pre-flight sul generatore dell'albero (v1.2.2, MUST — bug #23)

`riorg.py albero` esegue questo controllo da solo e si rifiuta di scrivere un albero che non lo passa;
`riorg.py albero --check FILE` lo applica a qualunque HTML già prodotto. Per `albero.ps1` vale il rito manuale.
`scripts/albero.ps1` arriva nella cache di sessione **come è salvato**: se in questa copia le
funzioni chiamate dagli handler inline non hanno il prefisso `ax`, l'albero che genera nasce con
«Espandi/Collassa» morti. **Quindi, prima di ogni uso di `albero.ps1`:**

1. Leggi lo script e conta le occorrenze di `function all(` e di `onclick='all(`.
2. Se ce n'è anche una sola, riscrivi **nella copia in uso** ogni funzione chiamata da `onclick`
   col prefisso `ax`, definizione e chiamata insieme:
   `all`→`axSetAll` · `tg`→`axtg` · `note`→`axnote` · `exportC`→`axexportC` ·
   `copyExp`→`axcopyExp` · `dlExp`→`axdlExp` · `setTag`→`axsetTag` · `saveNote`→`axsaveNote` ·
   `delNote`→`axdelNote`.
3. **Verifica prima di generare:** ogni `onclick='X(` deve avere la sua `function X(`. Zero orfane,
   zero `all(` residui non prefissati. Se la verifica non passa, non generare l'albero.
4. Sull'HTML già prodotto in passato, la stessa sostituzione lo ripara (backup `.bak` prima).

*Il fix appartiene al generatore, non all'artefatto: un fix applicato solo all'HTML si perde alla
generazione successiva, e la scheda del bug continua ad avere ragione.*

## Ambiente di esecuzione

| Dove gira | Fasi 0–2 (lettura) | Fase 3 (esecuzione) | Stato |
|---|---|---|---|
| Windows + PowerShell | `riorg.py` o `.ps1` | `execute.ps1` / `undo.ps1` (tutte le op) oppure `riorg.py` | collaudato (v1.2.x in produzione, bench 17/17) |
| Windows solo Python | `riorg.py` | `riorg.py` (no MERGE/FLATTEN) | bench 17/17 (30/09/2026) |
| macOS nativo (Python 3) | `riorg.py` | `riorg.py` (no MERGE/FLATTEN) | **beta: non collaudato su Mac** — prima run in sola lettura o sola-copia, bench prima di tutto |
| Shell Linux di lavoro (VM, cartelle condivise) | `riorg.py` | `riorg.py`, solo se i volumi sono scrivibili e sullo stesso dispositivo | bench 17/17 (Linux, 30/09/2026) |
| Nessun Python né PowerShell | comandi di shell aggregati, stessa logica | **bloccata**: resta lettura/proposta | — |

- **Cestino: non è una garanzia.** Sulle unità di rete (NAS, SMB) e su quelle rimovibili il Cestino di
  Windows non esiste; nelle shell di lavoro virtuali non esiste il Cestino del sistema ospite. Per questo
  ELIMINA è **quarantena** di default: rinomina sullo stesso volume, istantanea, invertibile.
- **Spostare fra volumi diversi è vietato** (diventerebbe copia + cancellazione): si usa COPIA, poi
  ELIMINA in quarantena, con due gate distinti.
- **macOS:** servono i permessi *File e cartelle* (Volumi di rete, Volumi rimovibili) per l'app Claude;
  NTFS è in sola lettura; i file `._*` e `.DS_Store` sono spazzatura e vengono ignorati.
- **Esegui FUORI dal mount Cowork.** Se il target è montato in Cowork, il processo del mount tiene
  handle aperti sulle directory: Windows nega move/rinomina di **cartelle intere** (`Access denied`,
  sharing violation) — i file singoli passano, i folder no. Quindi la Fase 3 va eseguita quando il
  target **non è montato** (o dopo averlo smontato). Fallback imperfetto: `execute.ps1 -AllowContentMove`
  sposta i file uno-a-uno in una cartella nuova e prova a rimuovere quella svuotata (può lasciare
  cartelle vuote se l'handle è ancora tenuto). Vedi `references/3_esecuzione.md` e Debug bug #18.
- **Script elevati:** se un passo richiede PowerShell come amministratore, **passa lo script da
  `[System.Management.Automation.Language.Parser]::ParseFile` prima di lanciarlo** e usa `-NoExit`.
  Una finestra elevata che si chiude nell'istante in cui si apre ha quasi sempre un errore di
  sintassi, e l'errore muore con la finestra: sembra un permesso negato e non lo è.

## Tassonomia a 2 strati

- **Mappa entità×dominio** (archivio, default): `[Entità]/[Dominio]/[Anno]` — dove *vive* il file.
- **Scala di attività** (vista, opzionale): 4 fasce **Attivo / Ricorrente / Riferimento / Archivio**
  derivate da metadati in `riorg_vista.json`; legge, **non sposta** mai i file.
La semantica (2b) alimenta entrambi gli strati. → `references/2d_tassonomia.md`

## Badge canonici (colori fissi, non modificabili)

RINOMINA blu · SPOSTA verde · MERGE ambra · ELIMINA rosso · CREA teal · FLATTEN viola · VERIFICA rosa.
**COPIA** (v1.3-beta) non ha un badge suo: usa **CREA** con la motivazione che comincia per «COPIA —»
(mai SPOSTA: chi approva deve leggere quello che succede davvero). ELIMINA nel widget dice «in quarantena».
Template statici in `assets/widget_template.html` (proposta, Fase 2) e `assets/widget_verifica_template.html` (verifica, Fase 4) — solo dati iniettati, mai riscrivere CSS/JS. Standard cross-progetto in `docs/REGOLE_WIDGET.md`.

## Regole non negoziabili

1. Mai eseguire operazioni senza dry-run prima.
2. Mai ELIMINA senza doppia conferma esplicita ("PROCEDI").
3. MERGE ed ELIMINA sempre a gate manuale, qualunque sia la confidence.
4. Eliminazione reversibile: **quarantena** `_DA_ELIMINARE` sullo stesso volume (default); Cestino solo opt-in su disco locale fisso. Disco esterno intoccato fino alla verifica.
5. Stato di ogni progetto isolato — nessuna interferenza tra progetti.
6. Badge HTML sempre con colori canonici fissi.
7. File ambiguo o confidence <0.50 → badge VERIFICA, aspetta l'utente.
8. MD5 solo sui candidati doppioni per dimensione, mai su tutti i file.
9. PDF scansionati: inclusi nella struttura ma badge VERIFICA "contenuto non letto".
10. Fasi 1–2: sola lettura, zero modifiche ai file.
11. Applicazioni / progetti di codice (`.git`, `node_modules`, `package.json`, `*.exe`…): non riorganizzare gli interni (rompe import/build). Si sposta o archivia solo il blocco intero come unità.
12. Esecuzione (Fase 3) solo con un motore collaudato per il sistema in uso (tabella «Ambiente di esecuzione»): `execute.ps1` su Windows, `riorg.py` dove il bench è passato. Su un sistema dove il bench non è ancora stato eseguito (macOS in v1.3-beta) si lancia **prima** `riorg.py bench` su una cartella locale; se non è 17/17, resta read-only.
13. Non eseguire move/rinomina di **cartelle** mentre il target è montato in Cowork → `Access denied`. Esegui fuori mount (vedi "Ambiente di esecuzione", Debug bug #18).
14. **Debrief albero obbligatorio**: nessuna riorg si chiude senza generare e presentare l'albero interattivo (`scripts/albero.ps1` o `riorg.py albero`) con commento per riga ed export risposte.
15. **Pre-flight sul generatore dell'albero** (v1.2.2): mai lanciare `albero.ps1` senza aver verificato il prefisso `ax` su tutte le funzioni chiamate da handler inline, e senza che ogni `onclick` abbia la sua funzione. Un fix applicato all'HTML e non al generatore non è un fix.
16. **Autocontrollo e metriche** (v1.3-beta): ogni comando stampa quanto ha letto, quanti candidati e hash, quanti errori di lettura; **uno zero si valida con un positivo noto** prima di scriverlo. Le metriche finiscono in `riorg_metrics.jsonl` nella cartella di stato.
17. **Mai spostare fra volumi diversi e mai due op sulla stessa destinazione** (v1.3-beta): su macOS e Linux una rinomina sovrascrive senza chiedere; la validazione lo impedisce, non va aggirata.

## Note operative per Claude

- **Pre-flight (= Fase 0a):** se il target non è esplicito nel prompt o non è montato/accessibile, FERMATI e chiedi su quale cartella agire, poi richiedi i permessi (`request_access`/mount) su quella. Mai assumere un percorso di default — niente `Desktop` hardcoded.
- **Headless/scheduled:** la Fase 0c non blocca — le domande qualitative vanno redatte nel report come "Da chiedere"; il flusso prosegue in sola lettura/proposta, mai esecuzione.
- Usa il nome progetto dell'utente (non inventarlo) per i file di stato.
- Ripresa sessione: leggi lo stato esistente (`riorg_cache.json` ecc.) e riparti dal punto giusto.
- Carica references e scripts on-demand: non inlinare ciò che è già in `scripts/`.
- Il flusso è sempre interrogazione → briefing → analisi → widget → conferma → esecuzione → verifica: non saltarlo.
- **Copia patchata di riferimento** del generatore: `scripts/albero.ps1` di questo pacchetto è già allineata (prefisso `ax`, verificata il 28/09/2026). Se una copia in uso non lo fosse, riallineala da qui. `riorg.py` porta lo stesso HTML e rifiuta di scrivere un albero che non passa il pre-flight.
- **Beta:** a fine run su un sistema nuovo, restituisci all'autore il **feedback** con il modello di `references/5_benchmark.md` (bench + metriche della run reale + attriti incontrati).
- **Python:** `python3` su macOS/Linux, `python` o `py` su Windows; se l'alias di Windows non risponde, cerca un `python.exe` reale prima di dichiararlo assente.

