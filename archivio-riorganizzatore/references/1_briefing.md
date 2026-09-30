# Briefing progressivo (Fase 1)

Front-load ridotto a **3 domande**. Tutto il resto è default dichiarato nel widget di
proposta, modificabile lì. Domande aggiuntive **solo** se lo scan rivela ambiguità reale.

## Pre-flight (prima delle 3 domande)

Prima di tutto, accertati di poter operare sul target:

- Se il **target non è esplicito** nel prompt, o **non è montato/accessibile**, FERMATI: chiedi su
  quale cartella agire e **richiedi i permessi** su quella (`request_access` / mount). Mai assumere un
  percorso di default — **niente `Desktop` hardcoded** (era la causa del blocco pre-flight del 31/05).
- Procedi con le 3 domande solo a **target confermato e accessibile**.

## Le 3 domande

1. **Target** — qual è la cartella da riorganizzare? (percorso assoluto)
2. **Obiettivo** — riordino / archiviazione / dedup? (uno o più)
3. **Vincoli intoccabili** — cosa NON va spostato, rinominato o eliminato? (cartelle, pattern, file critici)

## Default dichiarati (modificabili nel widget)

| Aspetto | Default |
|---|---|
| Tassonomia archivio | Mappa entità×dominio (`[Entità]/[Dominio]/[Anno]`) |
| Vista | Scala di attività disattivata (attivala per lo scadenziario) |
| Nomenclatura | `AAAA-MM-GG_descrizione`, suffissi `_BOZZA` / `_DEFINITIVO` |
| Prefissi macro-categorie | `01_`, `02_`, … |
| Dominio semantico | dedotto dallo scan; se misto → chiede l'asse |
| Dedup | MD5 solo sui candidati per dimensione |
| Eliminazione | sempre via Cestino + doppia conferma |

## Quando chiedere una 4ª domanda

- Dominio misto non risolvibile (es. visivo + finanziario nello stesso target) → chiedi l'asse prevalente.
- Vincolo ambiguo (es. "non toccare i lavori in corso" senza criterio) → chiedi il criterio operativo.

Le risposte vanno salvate in `riorg_briefing.md` nella cartella del progetto Claude.
