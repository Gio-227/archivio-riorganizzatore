# Tassonomia a 2 strati

I due metodi non si escludono: si **archivia** col preset-archivio; la **vista** è una lente che
legge metadati senza spostare nulla.

| Strato | Domanda | Metodo | Sposta i file? |
|---|---|---|---|
| **Mappa entità×dominio** (archivio) | dove *vive* il file | semantico: entità → dominio → anno | mai per invecchiamento |
| **Scala di attività** (vista) | cosa è *caldo* ora | fasce di azionabilità da metadati | **mai**: legge, non sposta |

## Mappa entità×dominio (default su disco)

```
[Entità]/                Azienda-A · Associazione-B · Personale · Commissioni …
└── [Dominio]/           visivo · amministrativo-legale · finanziario · operativo · corrispondenza
    └── [Anno]/          sotto-livello, mai categoria primaria
```

Stabile, discreto, ricostruibile da regole; adatto a storico/legale e ad archivi multimediali da centinaia di GB.

## Scala di attività (solo display)

Quattro fasce di azionabilità: **Attivo** (obiettivo/scadenza) · **Ricorrente** (responsabilità
continue) · **Riferimento** (riusabile) · **Archivio** (concluso/dormiente). Scadenziario derivato
dal metadato `scadenza`. "PARA" resta etichetta interna di sola vista — l'acronimo non appare mai
sull'archivio fisico.

## `riorg_vista.json` (runtime, per progetto)

```json
{ "schema": 1, "voci": {
  "<path-rel>": { "stato": "attivo", "scadenza": "2026-06-21", "nota": "catering 21/06" } } }
```

Default `archivio` se non dichiarato; lo stato cambia nel JSON, **mai** spostando il file. Il
widget v1.1 ha un toggle Archivio ⇄ Scala di attività.
