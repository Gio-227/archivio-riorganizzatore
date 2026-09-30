# archivio-riorganizzatore

[![bench](https://github.com/Gio-227/archivio-riorganizzatore/actions/workflows/bench.yml/badge.svg)](https://github.com/Gio-227/archivio-riorganizzatore/actions/workflows/bench.yml)
![versione](https://img.shields.io/badge/versione-1.3.0--beta-orange)
![licenza](https://img.shields.io/badge/licenza-Apache--2.0-blue)

**Una skill per Claude che mette ordine nelle cartelle senza rischiare i tuoi file.** Riorganizza, trova i doppioni e archivia su Windows, macOS e Linux. Ogni passo è mostrato prima, approvato da te e reversibile.

> **Beta.** Su Windows e Linux è collaudata: bench 17/17, e su Windows gira in produzione dalla v1.2. **Su macOS non ha ancora un uso reale alle spalle**: la CI la prova su un runner macOS a ogni commit, ma la prima run su un Mac vero è la tua. Il tuo feedback serve → [apri un feedback](../../issues/new?template=feedback-beta.md).

## Come lavora

Cinque fasi, sempre in quest'ordine: **Interroga → Mappa → Proponi → Esegui → Verifica**.

1. **Interroga.** Chiede su quale cartella lavorare e riconosce il sistema, gli strumenti e il tipo di disco (locale, rete, rimovibile).
2. **Mappa.** Fa l'inventario in sola lettura. Cerca i doppioni con l'MD5 solo sui file che potrebbero esserlo (stessa dimensione) e con un'impronta rapida sui file grandi.
3. **Proponi.** Prepara una pagina HTML dove approvi, modifichi o scarti ogni operazione.
4. **Esegui.** Prima una prova a vuoto che **blocca** i piani sbagliati, poi l'esecuzione con un journal che permette di annullare tutto.
5. **Verifica.** Rilegge il disco, fa quadrare i conti e genera un albero interattivo con un commento per ogni riga.

## Perché è sicura

| Rischio | Cosa fa la skill |
|---|---|
| Cancellare per errore | **Non cancella mai.** ELIMINA sposta in `_DA_ELIMINARE/` sullo stesso disco; la svuoti tu. Sui NAS e sui dischi rimovibili il Cestino non esiste: per questo niente Cestino di default |
| Eseguire un piano sbagliato | Prova a vuoto obbligatoria. Sorgente assente, destinazione occupata, due op sulla stessa destinazione, spostamenti fra dischi, spazio insufficiente → **si ferma** |
| Non poter tornare indietro | Ogni azione entra nel journal **prima** di essere fatta; `undo` riavvolge in ordine inverso |
| Rompere progetti e librerie | `.git`, `node_modules`, `.fcpbundle`, `.photoslibrary`, `.lrdata`, schede camera (`DCIM`…) si trattano come unità intere, mai smontate |
| Un «zero risultati» falso | Ogni comando stampa quanto ha letto, quanti hash ha calcolato e quanti errori ha incontrato. Uno zero va validato con un positivo noto |

## Sistemi supportati

| Sistema | Lettura e proposta | Esecuzione | Stato |
|---|---|---|---|
| Windows + PowerShell 5.1 | `riorg.py` o `.ps1` | `execute.ps1` / `undo.ps1` oppure `riorg.py` | collaudato |
| Windows, macOS, Linux con Python ≥3.8 | `riorg.py` | `riorg.py` (CREA, COPIA, SPOSTA, RINOMINA, ELIMINA in quarantena) | Linux e Windows collaudati · **macOS: solo CI, cerchiamo feedback** |

`riorg.py` usa **solo la libreria standard di Python**: non c'è niente da installare.

## Installazione

**Claude (app o web), account personale**
1. Settings → Capabilities → attiva **«Code execution and file creation»**.
2. Scarica [`dist/archivio-riorganizzatore_v1.3-beta.zip`](dist/archivio-riorganizzatore_v1.3-beta.zip).
3. Customize → Skills → **«+» → Upload a skill** → scegli lo zip. Non scompattarlo né rinominarlo.

**Claude Code**: copia la cartella `archivio-riorganizzatore/` in `~/.claude/skills/`.

Dentro il pacchetto, `HANDOFF_INSTALLAZIONE.md` spiega a Claude come verificare l'integrità e fare la prima prova.

## Prova in dieci secondi

```bash
python3 archivio-riorganizzatore/scripts/riorg.py bench --work /tmp/prova-riorg
```

Il bench crea una cartella sintetica con doppioni, trappole, zone protette e nomi con apostrofi, e ci fa passare l'intero ciclo:
- scan e dedup, anche fra due radici;
- un piano sbagliato, che deve essere rifiutato;
- dry-run, esecuzione reale, ripresa di una copia e undo con ripristino byte per byte;
- albero di verifica.

**Deve dire 17/17.** Scrive solo nella cartella indicata. Riferimenti misurati in [`references/5_benchmark.md`](archivio-riorganizzatore/references/5_benchmark.md).

## Comandi di `riorg.py`

| Comando | Cosa fa |
|---|---|
| `env <percorsi>` | sistema, strumenti, filesystem, tipo di unità, spazio libero |
| `scan --target T --state S` | inventario con cache, aggregato ≤40 righe, metriche |
| `dedup --target T --state S --partial` | doppioni dentro una radice |
| `dedup-multi --pair T S --pair T S … [--only lista.txt] --partial` | doppioni fra più radici (NAS, dischi) |
| `execute --ops ops.json --state S [--quarantine-root R] [--verify md5] [--real]` | esecuzione, dry-run di default |
| `undo --state S [--journal F] [--real]` | annullamento, dry-run di default |
| `albero --target T --out F` / `albero --check F` | albero di verifica HTML, con controllo dei pulsanti |
| `bench --work W [--scale medium] [--compare-ps dir]` | collaudo di correttezza e prestazioni |

## Struttura

```
archivio-riorganizzatore/   la skill (SKILL.md, references/, assets/, scripts/)
dist/                       lo zip pronto da caricare
tests/                      controlli statici e test PowerShell
tools/build_zip.py          rigenera lo zip in modo riproducibile
.github/                    CI (Linux · Windows · macOS), modelli di issue e PR
```

## Feedback e contributi

- **Hai provato la beta?** [Feedback beta](../../issues/new?template=feedback-beta.md): solo numeri e messaggi d'errore, mai nomi dei tuoi file.
- **Qualcosa non va?** [Bug](../../issues/new?template=bug.md).
- **Vuoi migliorarla?** Leggi [CONTRIBUTING.md](CONTRIBUTING.md) e apri una pull request: la CI deve essere verde sui tre sistemi.

## In English

*archivio-riorganizzatore* is a Claude skill (instructions in Italian) for reorganizing, de-duplicating and archiving messy folders on Windows, macOS and Linux.
- **Nothing is ever deleted:** discarded files go to a quarantine folder on the same volume.
- **Every step is previewed, approved and reversible:** dry-run, journal, undo.
- **Engines:** `riorg.py` (Python standard library only) and PowerShell scripts for Windows.
- **Test it:** `python3 archivio-riorganizzatore/scripts/riorg.py bench --work /tmp/riorg-test` must report 17/17.

macOS feedback is especially welcome. Issues and PRs in English are fine.

## Licenza

[Apache-2.0](LICENSE) © 2026 Gio-227
