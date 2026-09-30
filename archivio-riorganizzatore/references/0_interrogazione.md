# Fase 0 — Interrogazione iniziale (pre-scan)

Erede della regola "Bomba & Cannone" (MASTER): prima il cannone, poi la bomba.
Sola lettura, zero modifiche. Precede il briefing: niente scan profondo senza contesto.

## 0a — Target + permessi

Target esplicito nel comando → confermalo e verifica mount/accesso.
**Sistema e motore (v1.3-beta):** `python3 scripts/riorg.py env <percorsi>` → sistema, strumenti, filesystem,
tipo di unità (locale / rete / rimovibile / cartella di VM). Su rete e rimovibili il Cestino non c'è:
ELIMINA solo in quarantena. Sistema mai collaudato → `riorg.py bench` su una cartella locale prima della Fase 3.
Target assente → **FERMATI e chiedi** (prima domanda). Mai un percorso di default hardcoded.

## 0b — Precontesto quantitativo (1–2 call aggregate, output ≤40 righe)

- GB + n° file per sottocartella
- estensioni dominanti
- pattern di naming (versioni multiple, prefissi, date)
- file di log
- volumi grossi
- repo git annidati → **zone protette** (interni esclusi da scan/dedup, `-ExcludeProtected` default on)
- cartelle vuote

## 0c — Interrogazione qualitativa (all'utente)

- natura/uso della cartella
- logica archivio preferita (PARA / entità / stato / cronologico)
- cosa ottimizzare (spazio, ritrovabilità, token, handoff)
- cross-progetto che contano

*Headless/scheduled: NON bloccare — domande redatte nel report come "Da chiedere", flusso continua in sola lettura/proposta.*

## 0d — Visione sistemica

Classifica per nature (storico · codice · moduli · istruzioni richiamabili) e proponi
una lettura d'insieme, non ritocchi. Output: tabella **natura → zona → proposta**.

## Gate

Le Fasi 1–2 partono solo con: **0a ok · 0b ok · 0c risposta o differita · 0d redatta.**
