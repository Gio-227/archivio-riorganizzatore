# Semantica — dominio VISIVO (EXIF + vision)

Classifica le immagini per **utilizzo finale**, non per tipo file o data: come verranno usate?
per cosa servono? chi le userà?

## 1. EXIF/XMP prima di tutto

```powershell
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile("C:\percorso\immagine.jpg")
$propItems = $img.PropertyItems
# 0x9003 data scatto · 0x010F/0x0110 dispositivo · 0x8825 GPS · 0x0131 software · 0x010E descrizione
$img.Dispose()
```

Batch EXIF → CSV con `scripts/exif.ps1`. Per RAW/XMP usa ExifTool se disponibile.

## 2. Vision diretta — solo se metadati poveri

Attiva se: EXIF assenti/corrotti, data inaffidabile (es. 01/01/2000 = reset fotocamera),
nessun dato su dispositivo/soggetto/luogo. Allora descrivi: soggetto principale, scena
(interno/esterno, prodotto, persona, paesaggio), mood (formale/informale/tecnico/emotivo),
utilizzo stimato (istituzionale, social, archivio tecnico).

## 3. Scheda catalogo per gruppo

GRUPPO · N file · formato principale · periodo · soggetto · utilizzo potenziale · cartella suggerita · note.

## 4. Tassonomia per utilizzo finale

| Utilizzo | Struttura | Note |
|---|---|---|
| Gestione marchio | `Marchio/Logo/`, `Marchio/Foto_Istituzionale/` | master separati dai derivati |
| Ritocco | `Fotografia/RAW/`, `Fotografia/Elaborati/` | RAW + JPG dello stesso scatto insieme |
| Video | `Video/Riprese_Grezze/`, `Video/Montaggi/` | non separare audio/video della stessa ripresa |
| Archivio storico | `Archivio/[anno]/[evento]/` | ordinamento cronologico |
