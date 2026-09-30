# Capability discovery + handoff (Fase 2c)

Dopo che `2b_semantica.md` ha rilevato i tipi, decide **se servono strumenti esterni** e instrada.
Sola lettura: proporre un'installazione non tocca il disco. Cache per non ripagare la discovery.

## Logica

1. **Inventario** delle capability installate nella sessione (`list_skills`, `list_plugins`).
2. Per ogni *need* derivato dai domini (es. `trascrizioni`, `ocr_pdf`, `audio`), **consulta la
   cache** `riorg_capabilities.json`:
   - need già risolto (tool trovato / nativo / già rifiutato) → **non interrogare di nuovo**;
   - need nuovo → prosegui al passo 3.
3. **Ragiona il match** e applica un esito:
   - capability **presente** → instrada e usa (es. trascrizioni → `stt-cleanup`);
   - **assente ma utile** → cerca nel registro (`search_mcp_registry`, `search_plugins`) e
     **proponi l'installazione** (`suggest_plugin_install` / `suggest_connectors`). Non installare
     tu: lo fa l'utente;
   - **nessuna serve** → procedi nativo.
4. Registra l'esito in cache (anche "declined"/"native") così le run successive non richiedono più.

Regola: chiedi all'utente di installare **solo** quando un tool serve davvero, manca, e non è già
stato scartato. Mai assumere capability non viste. "Instrada se disponibile."

## Cache — `riorg_capabilities.json` (per progetto)

```json
{ "schema": 1, "ts": "...", "needs": {
  "trascrizioni": { "tool": "stt-cleanup", "status": "available", "asked": true },
  "ocr_pdf":      { "tool": null,          "status": "declined",  "asked": true } } }
```

`status`: `available` (installata, instradata) · `missing` (assente, proposto install) ·
`declined` (utente ha rifiutato) · `native` (gestito dalla skill stessa). Solo i need assenti
dalla cache generano interrogazione/tool-call.
