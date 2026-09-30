<!-- Header Cowork v1.0 | Progetto: archivio-riorganizzatore | Tipo: handoff installazione skill | v1.1 | Generato: 2026-09-28 02:41 CEST | Aggiornato: 2026-09-30 18:10 CEST (v1.1 — skill v1.3-beta: Windows + macOS) | Da: sessione riorg Downloads — pacchetto per un altro utente Claude (account personale) -->

# Handoff — skill `archivio-riorganizzatore` v1.3-beta (Windows · macOS · Linux)

## Per la persona che riceve lo zip (due righe)

Hai due strade:
- **Veloce:** installa la skill da solo con i passi del §3.
- **Guidata:** apri una chat con Claude, allega **questo zip** e scrivi: *«Leggi HANDOFF_INSTALLAZIONE.md e aiutami a installare e provare la skill»*.

Lo zip da caricare è **questo stesso file**, così com'è: non va scompattato né rinominato dentro.

---

## Per Claude che legge questo file

### 1 · Cos'è
La skill riorganizza, deduplica e archivia una cartella disordinata sul computer dell'utente: Windows, macOS o Linux. È in **beta**: su Windows e Linux è collaudata, su macOS non ancora. Il flusso ha 5 fasi: **Interroga → Mappa → Proponi → Esegui → Verifica**.
- **Le fasi 0–2 sono sola lettura.** Producono un widget HTML di proposta, dove l'utente approva o scarta ogni operazione.
- **La fase 3 esegue** solo dopo un dry-run. Scrive un journal che permette l'undo. Non cancella mai: ELIMINA sposta in una cartella di quarantena, `_DA_ELIMINARE`, sullo stesso disco.
- **La fase 4 verifica** e genera un albero con un commento per ogni riga.

Le istruzioni complete sono in `SKILL.md`. Questo file serve solo a installarla e partire.

### 2 · Contenuto del pacchetto
| Percorso | A cosa serve |
|---|---|
| `SKILL.md` | istruzioni della skill (frontmatter `name: archivio-riorganizzatore`) |
| `references/` | 11 schede caricate su richiesta, una per fase: interrogazione, briefing, analisi, semantica, capability, tassonomia, esecuzione, verifica |
| `assets/widget_template.html` · `widget_verifica_template.html` | stampi statici dei widget: si iniettano solo i dati, CSS e JS non si toccano mai |
| `scripts/riorg.py` | **motore multi-sistema** (Python ≥3.8, solo libreria standard): `env` · `scan` · `dedup` · `execute` · `undo` · `albero` · `bench` |
| `scripts/scan.ps1` · `dedup.ps1` · `exif.ps1` | lettura su Windows con PowerShell: scansione con cache, MD5 solo sui candidati, EXIF |
| `scripts/execute.ps1` · `undo.ps1` | esecuzione su Windows: dry-run validante, journal per run, quarantena, ritorno indietro in ordine inverso |
| `scripts/albero.ps1` | albero di verifica finale su Windows, **già corretto** per il bug dei pulsanti (vedi §4) |
| `references/5_benchmark.md` | bench, numeri di riferimento misurati, modello di feedback |
| `HANDOFF_INSTALLAZIONE.md` | questo file |

### 3 · Installazione (account personale: Free, Pro o Max)
Le skill caricate su un account personale non si condividono dall'app: si installano dallo zip, e i clic li fa l'utente. Guidalo così:
1. **Settings → Capabilities**: deve essere acceso **«Code execution and file creation»**. Senza questa opzione le skill non girano.
2. **Customize → Skills → «+» → Upload a skill** → scegliere questo zip.
3. Controllare che `archivio-riorganizzatore` compaia nell'elenco con l'**interruttore acceso**.
4. Se il caricamento dà errore sul nome, la causa è una: la cartella dentro lo zip deve chiamarsi esattamente `archivio-riorganizzatore`, come il `name` del frontmatter. Non rinominarla.

### 4 · Verifica di integrità da fare PRIMA di dire «installata»
Se lo zip ti arriva in chat, aprilo e controlla:
- [ ] `SKILL.md` esiste e il frontmatter ha `name: "archivio-riorganizzatore"`.
- [ ] **Pre-flight sull'albero (MUST).** In `scripts/albero.ps1` devono esserci **zero** `function all(` e zero `onclick='all(`. Ogni `onclick='X(` deve avere la sua `function X(`: in questa copia tutte le funzioni portano il prefisso `ax` (`axSetAll`, `axtg`, `axnote`…).
  *Perché conta:* senza prefisso, negli handler inline `all(...)` finisce su `document.all` e i pulsanti Espandi/Collassa non fanno niente, senza nessun errore in console.
- [ ] Con Python: `python3 scripts/riorg.py albero --check <un html>` e soprattutto **`python3 scripts/riorg.py bench --work <cartella nuova su disco locale>` → deve dire 17/17**. Su un sistema dove la skill non è mai girata (macOS in questa beta), il bench viene **prima** di qualunque esecuzione.
- [ ] Opzionale, su Windows: ogni `.ps1` supera `[System.Management.Automation.Language.Parser]::ParseFile` con 0 errori.

Riporta l'esito in chiaro: controllo passato o no, e su quale riga. *Un controllo che non trova nulla non è un OK finché non hai visto che sa trovare qualcosa.*

### 5 · Requisiti per usarla davvero
- **Le fasi 0–2 (lettura e proposta)** girano ovunque tu possa leggere la cartella.
- **La fase 3 (esecuzione)** richiede uno dei due motori:
  - `execute.ps1` su Windows con PowerShell;
  - `riorg.py` su qualunque sistema con Python ≥3.8 **dove il bench è 17/17**.

  Senza nessuno dei due, la skill resta in sola lettura, per regola. La tabella completa è in `SKILL.md` → «Ambiente di esecuzione».
- **Cestino:** sui NAS e sui dischi rimovibili non esiste. Per questo ELIMINA va sempre in quarantena sullo stesso volume.
- **macOS:** l'app Claude ha bisogno dei permessi *File e cartelle* per i Volumi di rete e rimovibili. NTFS è in sola lettura.
- Serve l'**app desktop Claude** con la cartella collegata alla sessione.
- **Se Windows nega lo spostamento di cartelle intere** (`Access denied`), la cartella è tenuta aperta dal collegamento della sessione. Rimedio:
  - eseguire con la cartella non collegata;
  - oppure usare `execute.ps1 -AllowContentMove`, che sposta i file uno per uno.
- **Stato per progetto:** la skill scrive `riorg_cache.json`, `riorg_undo*.json` e i report in `Documents\Claude\Projects\[NomeProgetto]\`. Il nome del progetto lo sceglie l'utente, non inventarlo.

### 6 · Primo giro consigliato
Una cartella piccola e sacrificabile, per esempio una copia di `Downloads` con 20–30 file. Prompt tipo:
> *«Riorganizza la cartella C:\Users\…\Downloads\prova-riorg»*

Aspettati questa sequenza:
1. le domande della Fase 0;
2. un widget di proposta;
3. il dry-run;
4. la parola **PROCEDI** per le eliminazioni;
5. il widget di verifica;
6. l'albero finale.

### 7 · Regole che non si piegano (sintesi di `SKILL.md`)
1. Mai eseguire senza dry-run prima.
2. MERGE ed ELIMINA sempre a gate, con doppia conferma esplicita («PROCEDI»).
3. Eliminazione solo via Cestino, mai `Remove-Item` distruttivo.
4. Confidenza sotto 0,50 → badge VERIFICA: decide l'utente.
5. MD5 solo sui file candidati per dimensione, mai su tutto.
6. Progetti di codice (`.git`, `node_modules`…): mai toccare gli interni. Si spostano solo come blocco intero.
7. Nessuna riorganizzazione si chiude senza l'albero di debrief.

### 8 · Riferimenti che troverai citati ma non sono nel pacchetto
- **«Debug bug #18», «bug #23», «Bomba & Cannone (MASTER)»**: rimandi al registro interno dell'autore. Il contenuto che serve è già scritto per esteso in `SKILL.md`:
  - #18 = cartella collegata → `Access denied` sulle cartelle;
  - #23 = pulsanti morti dell'albero;
  - Bomba & Cannone = prima strumenti e permessi, poi il lavoro.
- **`docs/REGOLE_WIDGET.md`**: standard dei widget dell'autore, non incluso. La regola operativa è una: nei template si iniettano dati, CSS e JS non si riscrivono.

### 8-bis · Beta: restituisci il feedback
Alla prima run su un sistema nuovo compila il **modello di feedback** di `references/5_benchmark.md` e consegnalo all'utente, che lo inoltra all'autore. Allega il JSON del bench e `riorg_metrics.jsonl`. Nel feedback vanno numeri e messaggi d'errore, non nomi di file dell'utente.

### 9 · Lezioni dal campo (run reale del 27–28/09/2026, 158 file)
- **Uno zero si valida con un positivo noto.** Una ricerca di doppioni ha risposto «0 su 157» ed era falso: lo ha smascherato un file di cui si conoscevano tre copie. Ogni script di confronto deve stampare il suo autocontrollo, cioè quanti candidati ha trovato e quanti hash ha calcolato.
- **Lo stato si rilegge dal disco, non dal messaggio di successo.** Dopo la run: MD5 delle destinazioni, sorgenti sparite, voci nel Cestino, copie di riferimento ancora al loro posto.
- **Un hardlink non è una copia d'archivio.** File scaricati dalle chat possono essere hardlink alla cache dell'app Claude.
- **Uno zip scompattato altrove è un contenitore ridondante solo se ogni sua voce ha il gemello MD5.**

### 10 · Differenze rispetto alla copia dell'autore
- In `SKILL.md` il percorso della «copia patchata» puntava al PC dell'autore: ora punta a `scripts/albero.ps1` di questo pacchetto.
- Esclusi il `README.md` del repository e un file di backup (`albero.ps1.bak`).
- v1.3-beta, cosa è cambiato:
  - aggiunti `riorg.py` e `references/5_benchmark.md`;
  - ELIMINA in quarantena su `execute.ps1` e `undo.ps1`;
  - `dedup.ps1` non tratta più i file vuoti come doppioni.
- **Licenza:** Apache-2.0 © 2026 Gio-227.
