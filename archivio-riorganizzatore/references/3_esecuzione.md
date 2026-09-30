# Esecuzione (Fase 3)

Traduce le decisioni del widget in operazioni reali, con dry-run obbligatorio e journal per l'undo.

## Prima di tutto: quale motore (v1.3-beta)

`python3 scripts/riorg.py env <target> <destinazione> <radice-quarantena>` dice il sistema, gli
strumenti, il filesystem e il tipo di unità di ogni percorso. Da lì:

| Situazione | Motore | Op disponibili |
|---|---|---|
| Windows con PowerShell | `execute.ps1` / `undo.ps1` (collaudati in produzione) | CREA · SPOSTA · RINOMINA · MERGE · FLATTEN · ELIMINA |
| Qualunque sistema con Python ≥3.8 dove il **bench è 17/17** | `riorg.py execute` / `riorg.py undo` | CREA · **COPIA** · SPOSTA · RINOMINA · ELIMINA |
| Sistema su cui il bench non è ancora passato (macOS in v1.3-beta) | nessuno finché non si lancia `riorg.py bench` su una cartella locale | — |
| Né Python né PowerShell | nessuno: resta lettura/proposta | — |

## ELIMINA = quarantena (default su ogni motore)

- **Windows:** `execute.ps1 ... -QuarantineRoot <radice>`. **Ogni sistema:** `riorg.py execute ... --quarantine-root <radice>`.
- Il file va in `<radice>/_DA_ELIMINARE/<run_id>/<percorso relativo>` **sullo stesso volume**. È una rinomina: istantanea, senza copia, invertibile dall'undo. Lo svuotamento lo fa l'utente, quando ha riletto.
- **Perché non il Cestino:**
  - sulle unità di rete (NAS, SMB) e su quelle rimovibili il Cestino di Windows non esiste;
  - nelle shell di lavoro virtuali non c'è il Cestino del sistema ospite.

  Il Cestino resta come `execute.ps1 -DeleteMode Cestino`, accettato **solo su dischi locali fissi**: la validazione lo rifiuta altrove.
- ELIMINA resta sempre a gate, con doppia conferma «PROCEDI».

## COPIA (v1.3-beta, solo `riorg.py`)

- Copia un file o una cartella intera (pacchetti, schede camera), creando le cartelle che mancano; ognuna finisce nel journal.
- **Ripresa:** un file già presente con la stessa dimensione non si ricopia. Una destinazione occupata con contenuto diverso ferma tutto.
- **Verifica:** `--verify size` (default) oppure `--verify md5`, che rilegge sorgente e copia.
- **Scrittura atomica:** prima un file `.riorg-part`, poi la rinomina. Una copia interrotta non lascia file a metà con il nome buono.
- **Undo:** toglie solo le copie che hanno ancora la dimensione registrata. Non tocca mai l'originale.

## Validazione (dry-run, e di nuovo prima del reale)

WARN, e il reale non parte, se:
- la sorgente è assente o la destinazione è già occupata;
- **due op hanno la stessa destinazione**: su macOS e Linux una rinomina sovrascrive senza chiedere;
- **SPOSTA o RINOMINA passano fra volumi diversi**: diventerebbe copia più cancellazione, quindi si usa COPIA e poi ELIMINA in quarantena;
- manca lo spazio per le copie (con un margine del 5%);
- la quarantena è su un altro volume, o manca;
- l'op è MERGE o FLATTEN su `riorg.py`: vanno spezzate in SPOSTA, oppure si usa `execute.ps1`.

## Ambiente & mount (pre-esecuzione)

- **Fuori dal mount Cowork.** Se il target è collegato alla sessione, il collegamento può tenere aperte le cartelle e Windows nega lo spostamento di cartelle intere (`Access denied`); i file singoli passano.
  - In dubbio, fai un test su una cartella sacrificabile invece di dare il blocco per scontato.
  - Fallback su Windows: `execute.ps1 -AllowContentMove`. Vedi Debug bug #18.
- **macOS:** permessi *File e cartelle* (Volumi di rete, Volumi rimovibili) all'app Claude; NTFS è in sola lettura.

## Flusso

1. Leggi `riorg_risposte.md` (decisioni esportate dal widget) e scrivi `ops.json`: `[{"tipo","da","a"}]`, percorsi assoluti.
2. Dry-run: `execute.ps1` (default `-DryRun $true`) oppure `riorg.py execute` (senza `--real`).
3. Dry-run pulito, cioè 0 WARN → conferma esplicita (per ELIMINA «PROCEDI») → reale (`-DryRun:$false` oppure `--real`).
4. WARN → fermati, mostra i problemi, aspetta istruzioni.
5. Genera `riorg_esecuzione.md` (op completate, errori, VERIFICA aperti) e verifica **dal disco**.

## Ordine operazioni

`execute.ps1`: **CREA → SPOSTA → RINOMINA → MERGE → FLATTEN → ELIMINA**.
`riorg.py`: **CREA → COPIA → SPOSTA → RINOMINA → ELIMINA**.

## Autonomia — modalità "b"

| Operazione | Confidence ≥0.85 | Confidence <0.85 |
|---|---|---|
| CREA / COPIA / SPOSTA / RINOMINA | **auto**, registrate nel journal | widget / VERIFICA |
| MERGE | **sempre gate** (conferma) | gate |
| ELIMINA (quarantena) | **sempre gate** + doppia conferma «PROCEDI» | gate |

## Journal e undo

- **`execute.ps1`:** `riorg_undo_<run_id>.json` + `riorg_undo.json` («ultima run»), schema 2 `{n, seq, tipo, da, a, nota}`.
  - `undo.ps1` deriva le inverse ed esegue in ordine LIFO con `-LiteralPath`, mai `Invoke-Expression`.
  - ELIMINA con `nota: quarantena` torna al suo posto e le cartelle di quarantena vuote spariscono; ELIMINA via Cestino resta manuale.
- **`riorg.py`:** `riorg_undo_<run_id>.jsonl`, una riga per azione scritta **prima** dell'azione con `fsync`, più `riorg_undo_last.txt`.
  - `riorg.py undo [--journal F] [--real]` inverte in ordine LIFO: rinomine e spostamenti tornano indietro, le copie si tolgono, le cartelle create si rimuovono solo se vuote.
  - Mai rimozioni ricorsive.
- **Si annulla con lo stesso motore che ha eseguito.**
