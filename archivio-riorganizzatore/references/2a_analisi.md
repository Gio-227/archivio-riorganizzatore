# Analisi e proposta (Fase 2)

Sola lettura: scan + dedup + semantica + confidence gate → proposta nel widget. Zero modifiche ai file.

## Flusso

1. `scripts/riorg.py scan --target <t> --state <s>` (ogni sistema) oppure `scripts/scan.ps1 <target>` (Windows) → CSV su disco + aggregato ≤40 righe in context (cartelle vuote,
   file sfusi, typo nei nomi, candidati duplicati per dimensione).
2. `scripts/riorg.py dedup --partial` oppure `scripts/dedup.ps1` → size-group, poi MD5 **solo** sui candidati; scrive gli hash in cache.
3. Semantica di dominio on-demand: dispatcher `2b_semantica.md` → moduli `2b_semantica_visivo.md`,
   `2b_semantica_amministrativo.md`, `2b_semantica_finanziario.md`. Dominio misto → più moduli, risultati separati.
4. Capability discovery/handoff: `2c_capability.md` (instrada a tool esterni se disponibili).
5. Confidence gate per ogni classificazione (sotto).
6. Mappa il risultato sulle due tassonomie (`2d_tassonomia.md`): archivio + vista.
7. Popola `assets/widget_template.html` con i dati reali → salva `[NomeProgetto]_proposta.html`.

## Confidence gate (formula)

> Score = 0.30×Hash + 0.25×Nome + 0.20×Path + 0.10×Estensione/MIME + 0.15×Content.
> Soglie: ≥0.85 auto, 0.50-0.85 widget, <0.50 verifica manuale.

- **≥0.85** → auto-proposta (badge normale; eseguibile in autonomia "b" per CREA/SPOSTA/RINOMINA).
- **0.50–0.85** → entra nel widget con nota di dubbio, decide l'utente.
- **<0.50** → badge VERIFICA, resta gate manuale.

Soglie nel frontmatter di `SKILL.md`, override via briefing.

## Cache anti-rilettura — `riorg_cache.json`

Chiave `path+mtime+size`. Hit (invariati) → riusa `md5`/`classe` senza I/O. Miss → ricalcola e
aggiorna. La Fase 4 fa diff cache↔disco, **non** ri-scan. Invalidazione totale solo con `--no-cache`.

```json
{ "schema": 1, "scan_ts": "...", "files": {
  "<path-rel>": { "size": 0, "mtime": "...", "md5": "opz", "classe": "opz", "conf": 0.0 } } }
```

Regola token: mai ri-hash né ri-leggere un file già in cache con stessi `path+mtime+size`.
