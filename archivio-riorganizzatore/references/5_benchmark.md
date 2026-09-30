# Benchmark e feedback (v1.3-beta)

Due prove, con scopi diversi. Servono entrambe.
- **A · Bench su cartella sintetica.** È uguale su ogni computer, quindi si confronta fra sistemi e fra versioni.
- **B · Metriche della run reale.** Dicono come si comporta la skill sui dati veri: NAS, dischi, TB. Si confrontano solo i **ritmi**, cioè file al secondo, MB al secondo, errori ogni 1.000 file.

## A · Bench

```
python3 scripts/riorg.py bench --work <cartella NUOVA su disco LOCALE> [--scale medium] [--compare-ps <cartella con i .ps1>]
```

Il bench crea da sé una cartella di prova e scrive **solo lì**. Mai lanciarlo su un NAS o su un archivio vero. Dura pochi secondi. `--compare-ps` (solo Windows) misura anche `scan.ps1` e `dedup.ps1` sulla stessa cartella.

**Cosa contiene la cartella di prova (scala small):**
- 279 file veri, 6 gruppi di doppioni identici (uno da più di 2 MB);
- due trappole per i doppioni:
  - file con la stessa dimensione ma contenuto diverso;
  - due file da 3 MB con testa e coda identiche e il centro diverso;
- 3 zone protette: `.git`, `node_modules`, `.fcpbundle`;
- una scheda camera (`DCIM`) e 5 file di spazzatura di sistema;
- nomi con apostrofi, accenti, parentesi e doppi spazi.

**I 17 controlli.** Tutti devono passare; con anche un solo FAIL la Fase 3 resta bloccata su quel sistema.

| Controllo | Cosa dimostra |
|---|---|
| `scan_conta_file` | l'inventario conta esattamente i file veri |
| `scan_unita_protette` | `.git`, `node_modules` e i pacchetti sono unità intere, gli interni esclusi |
| `scan_spazzatura_esclusa` | `.DS_Store`, `._*`, `Thumbs.db`, `@eaDir`, `#recycle` fuori dall'inventario |
| `scan_zero_errori` | nessuna cartella illeggibile passata sotto silenzio |
| `dedup_gruppi_esatti` | trova tutti e soli i doppioni: le trappole non passano |
| `dedup_fra_radici` | trova i doppioni fra due radici scansionate a parte, come due NAS (`dedup-multi`) |
| `validazione_ferma_i_piani_sbagliati` | un piano sbagliato viene rifiutato senza scrivere nulla (destinazione occupata, sorgente assente, doppia destinazione, MERGE, ELIMINA senza quarantena) |
| `dryrun_zero_warn` · `dryrun_nessuna_scrittura` | il dry-run valida e non tocca il disco |
| `reale_esito` · `copie_identiche_md5` · `sorgenti_delle_copie_intatte` | le copie sono identiche (file e pacchetto) e gli originali non cambiano |
| `elimina_in_quarantena` | ELIMINA non cancella: sposta in `_DA_ELIMINARE` |
| `ripresa_senza_ricopiare` | una copia interrotta e rilanciata non ricopia ciò che c'è già |
| `undo_ripristino_esatto` · `undo_nessun_residuo` | l'undo riporta la cartella byte per byte com'era, senza residui |
| `albero_preflight_ax` | l'albero di debrief nasce con i pulsanti funzionanti (bug #23) |

## Riferimenti misurati

### Bench (misurato il 30/09/2026, riorg.py 1.3.0-beta definitivo della beta)
| Sistema | Motore | Scala | Controlli | scan | dedup | ritmo scan | hash |
|---|---|---|---|---|---|---|---|
| Linux (spazio di lavoro Claude, ext4, Python 3.11) | riorg.py | small (279 file) | **17/17** | 0,010 s | 0,082 s | 28.821 file/s | 511 MB/s |
| Linux (idem) | riorg.py | medium (1.299 file) | **17/17** | 0,059 s | 0,224 s | 22.245 file/s | 491 MB/s |
| Windows 10 (PC dell'autore, NTFS, Python 3.13) | riorg.py | small | **17/17** | 0,030 s | 0,241 s | 9.401 file/s | 169 MB/s |
| Windows 10 (idem) | riorg.py | medium | **17/17** | 0,091 s | 1,019 s | 14.311 file/s | 102 MB/s |
| Windows 10 (idem) | **v1.2.2** `scan.ps1` + `dedup.ps1` | small | conta **299 / 279** · gruppi **7 / 6** | 0,77 s* | 1,41 s* | — | — |
| Windows 10 (idem) | **v1.2.2** `scan.ps1` + `dedup.ps1` | medium | conta **1.319 / 1.299** · gruppi **31 / 30** | 1,19 s* | 3,44 s* | — | — |
| Windows 10 (idem) | **v1.3** `scan.ps1` + `dedup.ps1` (corretto) | medium | conta 1.319 / 1.299 · gruppi **30 / 30** | 1,22 s* | 3,07 s* | — | — |

\* I tempi di PowerShell comprendono l'avvio del processo, circa mezzo secondo: non confrontarli al millisecondo con Python.

**Cosa ha scoperto il bench sulla v1.2.2:**
- **`dedup.ps1` raggruppava i file vuoti come doppioni:** 38 file da 0 byte in un solo gruppo. Corretto in v1.3.
- **`scan.ps1` conta nell'inventario la spazzatura di sistema e gli interni dei pacchetti:** +20 file sulla cartella di prova. È una differenza voluta, non un errore, ma `riorg.py` è più pulito anche su Windows.

**Il ritmo di copia del bench non indica niente.** Sono file piccoli e il journal fa `fsync` a ogni operazione. Il ritmo vero si legge nella run reale, sui file video.

### Run reali con la v1.2.x (Windows, PowerShell)
| Data | Cartella | Numeri | Esito |
|---|---|---|---|
| 28/09/2026 | Downloads (v1.2.2) | 158 file, 89,0 MB · 73 op (2 CREA, 8 SPOSTA, 63 ELIMINA) in 8 s | dry-run 0 WARN · 0 errori · verifica 158/158 · 0 imprevisti |
| 21/08/2026 | Desktop + Downloads (v1.2.1) | 728 file · 671 op (12 CREA, 611 SPOSTA, 48 ELIMINA) | 0 errori · 0 WARN |

Lezione che ha fatto nascere la regola 16: il 27/09 uno script di confronto fatto al volo, non della skill, ha dichiarato «0 doppioni su 157». Era falso, e lo ha smascherato un file di cui si conoscevano tre copie.

## B · Metriche della run reale

Ogni comando di `riorg.py` aggiunge una riga a `<stato>/riorg_metrics.jsonl`: durata, file, byte, file al secondo, hash in MB/s, copia in MB/s, errori di lettura, WARN, operazioni fatte. Sui NAS i ritmi dipendono dalla rete: annota il tipo di collegamento (cavo o Wi-Fi, 1 Gbit o altro).

## Modello di feedback — da restituire all'autore dopo la prima run su un sistema nuovo

File `feedback_riorg_<sistema>_<AAAA-MM-GG>.md`, con allegati il JSON del bench e `riorg_metrics.jsonl`.

```markdown
# Feedback archivio-riorganizzatore v1.3-beta — {sistema} — {data}
## Ambiente
sistema e versione · Python · come gira Claude (shell nativa / spazio di lavoro virtuale) · volumi (tipo, filesystem, rete)
## Bench
esito N/17 · tempi scan/dedup/execute/undo · ritmi · FAIL (quali, con il messaggio)
## Run reale
file letti · TB · file/s per volume · errori di lettura · candidati → hash → gruppi · GB copiati · MB/s di copia · WARN in dry-run · gate rispettati (sì/no)
## Confronto con i riferimenti
dove siamo sopra o sotto, e perché (hardware, rete, dati)
## Attriti
permessi · percorsi · strumenti mancanti · messaggi poco chiari · cose che la skill ha sbagliato o quasi sbagliato
## Cosa cambierei
al massimo 5 righe, in ordine di importanza
```

**Privacy.** Nel feedback non compaiono nomi di file o cartelle dell'utente, salvo quelli necessari a spiegare un errore, e mai materiale di terzi. Bastano numeri e messaggi d'errore.
