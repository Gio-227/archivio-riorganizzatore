## Cosa cambia e perché

## Checklist
- [ ] Il bench è verde su Linux, Windows e macOS (CI `bench`)
- [ ] Nessuna operazione distruttiva nuova: niente cancellazioni, ELIMINA solo in quarantena, journal scritto **prima** di ogni azione
- [ ] Se ho cambiato il comportamento di `riorg.py`, ho aggiunto o aggiornato un controllo del bench
- [ ] `riorg.py` usa solo la libreria standard e gira con Python 3.8+; gli `.ps1` con PowerShell 5.1
- [ ] Template dei widget: solo dati, CSS/JS invariati (o la PR riguarda proprio i template, e lo dice)
- [ ] Handler inline dell'albero con prefisso `ax`
- [ ] Nessun dato personale (nomi, percorsi, file reali) in codice, test, issue o commit
- [ ] `CHANGELOG.md` aggiornato; `dist/` rigenerato con `python tools/build_zip.py` se cambia il pacchetto
