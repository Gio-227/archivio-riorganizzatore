# Contribuire

Grazie! La skill tocca i file delle persone: per questo le regole sotto non sono di stile, sono di sicurezza.

## Regole che una PR non può rompere

1. **Nessuna cancellazione.** ELIMINA sposta in quarantena (`_DA_ELIMINARE/` sullo stesso volume). Niente `rm`, `Remove-Item` distruttivi, `shutil.rmtree` su dati dell'utente, niente `rsync --delete`.
2. **Dry-run prima del reale.** La validazione blocca: sorgente assente, destinazione occupata, destinazioni duplicate, spostamenti fra volumi, spazio insufficiente.
3. **Journal prima dell'azione.** Ogni operazione (cartelle create automaticamente comprese) si registra *prima* di essere eseguita; l'undo deve poter riportare tutto com'era.
4. **Zone protette intere.** Repository, pacchetti (`.fcpbundle`, `.photoslibrary`…), schede camera: mai smontati.
5. **Autocontrollo.** Ogni comando dice quanto ha letto e quanti errori ha incontrato; uno zero non si dichiara senza un positivo noto.
6. **Albero: prefisso `ax`** su ogni funzione chiamata da `onclick` (in un handler inline `all(...)` finisce su `document.all` e non fa niente, senza errori).
7. **Widget:** nei template si iniettano dati; CSS e JS si cambiano solo in PR dedicate.

## Vincoli tecnici

- `riorg.py`: **solo libreria standard**, Python ≥3.8, un solo file.
- `.ps1`: PowerShell 5.1 (Windows di serie), `-LiteralPath` ovunque, mai `Invoke-Expression`.
- Testo della skill in italiano. Issue e PR in italiano o inglese.

## Come lavorare

```bash
python3 tests/validate_skill.py
python3 archivio-riorganizzatore/scripts/riorg.py bench --work /tmp/b1
python3 archivio-riorganizzatore/scripts/riorg.py bench --work /tmp/b2 --scale medium
# Windows, in PowerShell:
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_quarantena.ps1 -S archivio-riorganizzatore\scripts
```

- **Nuovo comportamento in `riorg.py`:** aggiungi un controllo al bench che lo dimostri, e se possibile uno che dimostri che il caso sbagliato viene rifiutato.
- **Cambia il pacchetto:** rigenera lo zip con `python3 tools/build_zip.py` e aggiorna `CHANGELOG.md` e la versione in `SKILL.md` e `riorg.py`.
- **CI:** la pull request passa solo con il bench verde su Linux, Windows e macOS.

## Privacy

Mai file, nomi o percorsi reali in codice, test, issue o commit. Per riprodurre un problema usa la cartella sintetica del bench.
