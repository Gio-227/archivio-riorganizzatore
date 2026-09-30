---
name: Feedback beta (bench + run reale)
about: Hai provato la v1.3-beta su un tuo sistema? Racconta come è andata — soprattutto su macOS.
title: "[feedback] <sistema> — <data>"
labels: feedback
---

<!-- Privacy: solo numeri e messaggi d'errore. Niente nomi di file o cartelle tuoi o di terzi. -->

## Ambiente
- Sistema e versione:
- Python (`python3 --version`):
- Come gira Claude (app desktop / Claude Code / shell nativa / spazio di lavoro virtuale):
- Volumi coinvolti (tipo e filesystem da `riorg.py env`: locale, rete, rimovibile…):

## Bench
Comando: `python3 archivio-riorganizzatore/scripts/riorg.py bench --work <cartella nuova locale> [--scale medium]`
- Esito (N/17):
- Tempi scan / dedup / execute / undo:
- Ritmi (file/s, MB/s hash):
- FAIL (quale controllo e messaggio):

<!-- Allega il JSON del bench. -->

## Run reale (se c'è stata)
- File letti · TB · file/s per volume:
- Errori di lettura:
- Candidati → hash → gruppi di doppioni:
- GB copiati · MB/s:
- WARN in dry-run · gate rispettati (sì/no):

## Attriti
Permessi, percorsi, strumenti mancanti, messaggi poco chiari, cose che la skill ha sbagliato o quasi sbagliato.

## Cosa cambieresti (max 5 righe)
