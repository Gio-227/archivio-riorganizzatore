# Semantica — dispatcher (Fase 2b)

Entry della semantica: dopo lo scan (2a), capisce **che tipologie** ha davanti, instrada al
modulo giusto, e alimenta **entrambe le tassonomie**. Sola lettura.

## 1. Classifica il dominio

Dai nomi, estensioni, struttura e (se serve) contenuto, assegna a ogni gruppo un dominio:

| Dominio | Modulo | Segnale tipico |
|---|---|---|
| visivo | `2b_semantica_visivo.md` | jpg/png/raw/tiff, EXIF |
| amministrativo | `2b_semantica_amministrativo.md` | pdf con testo, atti, protocolli |
| finanziario | `2b_semantica_finanziario.md` | fatture, .p7m, importi, IVA |
| **nuovo/sconosciuto** | — | tipo non coperto sopra |

Dominio nuovo → **proponi un nuovo profilo** (es. audio, CAD, progetti) descrivendone segnale e
struttura suggerita; non forzarlo dentro un dominio esistente. Dominio misto → applica più moduli,
risultati separati.

## 2. Alimenta le due tassonomie (sempre)

Dallo stesso giudizio derivano due output, mai uno solo:

- **Archivio** (dove vive): dominio → `[Entità]/[Dominio]/[Anno]` (Mappa entità×dominio).
- **Vista** (quanto è caldo): azionabilità → stato `attivo / ricorrente / riferimento / archivio`
  in `riorg_vista.json` (Scala di attività). Legge, non sposta.

Dettaglio in `2d_tassonomia.md`.

## 3. Rilevamento applicazioni / codice → NON riorganizzare gli interni

Se la cartella contiene un'applicazione o un progetto di codice — segnali: `.git/`,
`node_modules/`, `package.json`, `requirements.txt`, `*.sln`/`*.csproj`, `*.exe` + struttura
di supporto, `venv/`, `build/` — **non proporre spostamenti/rinomine interni**: rompono import,
path relativi, build. Marca l'intera cartella come **zona protetta** (badge VERIFICA, nota
"applicazione/codebase — interni non riorganizzabili"). Si può archiviare/spostare il blocco
*intero* come unità, mai sventrarlo. Una vera modalità dev-aware è fuori scope (skill futura).

## 4. Handoff capability

Note i domini, passa a `2c_capability.md`: verifica se servono strumenti esterni (es.
trascrizioni → `stt-cleanup`, OCR per PDF scansionati) e instrada se disponibili.
