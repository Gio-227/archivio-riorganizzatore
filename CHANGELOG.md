# Changelog

## 1.3.0-beta — 2026-09-30
- **Multi-sistema.** Nuovo motore `scripts/riorg.py` (Python, solo libreria standard): `env`, `scan`, `dedup`, `dedup-multi`, `execute`, `undo`, `albero`, `bench`. Windows, macOS, Linux.
- **ELIMINA = quarantena** su tutti i motori (`_DA_ELIMINARE/<run_id>/` sullo stesso volume, reversibile). Il Cestino resta solo opt-in su dischi locali fissi (`execute.ps1 -DeleteMode Cestino`): sulle unità di rete e rimovibili il Cestino non esiste.
- **Nuova op COPIA** (`riorg.py`): ripresa senza ricopiare, scrittura atomica, verifica dimensione o MD5.
- **Validazione bloccante**: destinazioni duplicate, spostamenti fra volumi, spazio insufficiente.
- **Doppioni fra più radici** (`dedup-multi`), con filtro `--only`.
- **Metriche e autocontrollo** in ogni comando (`riorg_metrics.jsonl`).
- **Bench con 17 controlli** su una cartella sintetica; CI su Linux, Windows e macOS.
- Corretti due difetti della v1.2.2 trovati dal bench:
  - `dedup.ps1` raggruppava i file vuoti come doppioni;
  - `scan.ps1` conta spazzatura di sistema e interni dei pacchetti (documentato; `riorg.py` li esclude).

## 1.2.2
- Albero di verifica: tutte le funzioni chiamate da `onclick` con prefisso `ax` (bug dei pulsanti Espandi/Collassa morti: `all()` risolveva su `document.all`). Pre-flight obbligatorio sul generatore.

## 1.2.1
- Undo con inverse strutturate, senza `Invoke-Expression`: i percorsi con apostrofo rompevano l'inversa.
- L'inversa di CREA rimuove solo cartelle vuote.
- Ordinamento stabile delle operazioni.
- Dry-run validante.
- Journal per run.
- Widget di verifica standard.

## 1.2
- Widget di proposta con albero interattivo attuale → proposto.
- Debrief albero obbligatorio con commento per riga ed export.

## 1.1
- Cache anti-rilettura, script in `scripts/`, briefing progressivo, confidence gate, undo journal.
