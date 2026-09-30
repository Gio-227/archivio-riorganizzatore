<#
.SYNOPSIS
  exif.ps1 — Fase 2: lettura batch dei metadati EXIF delle immagini -> CSV.
.DESCRIPTION
  Estrae data scatto, dispositivo e software dalle immagini sotto -Target e scrive un CSV.
  I file senza data EXIF affidabile sono candidati per l'analisi visiva (vedi
  references/semantica_visivo.md). PowerShell 5.1+, usa System.Drawing.
.PARAMETER Target    Cartella con le immagini.
.PARAMETER StateDir  Cartella di stato del progetto. Default: cartella corrente.
#>
param(
  [Parameter(Mandatory)] [string] $Target,
  [string] $StateDir = ".",
  [string[]] $Ext = @(".jpg", ".jpeg", ".tif", ".tiff", ".png")
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function Get-ExifString($img, [int]$id) {
  $p = $img.PropertyItems | Where-Object { $_.Id -eq $id } | Select-Object -First 1
  if ($p) { return ([System.Text.Encoding]::ASCII.GetString($p.Value)).Trim([char]0) }
  return $null
}

$rows = New-Object System.Collections.Generic.List[object]
Get-ChildItem -LiteralPath $Target -Recurse -File -Force |
  Where-Object { $Ext -contains $_.Extension.ToLower() } | ForEach-Object {
    $rel = $_.FullName.Substring($Target.Length).TrimStart('\')
    $dateTaken = $null; $device = $null; $software = $null
    try {
      $img = [System.Drawing.Image]::FromFile($_.FullName)
      $dateTaken = Get-ExifString $img 0x9003   # DateTimeOriginal
      $device    = Get-ExifString $img 0x0110   # Model
      $software  = Get-ExifString $img 0x0131   # Software
      $img.Dispose()
    } catch { $software = "ERRORE LETTURA" }
    $rows.Add([pscustomobject]@{ path = $rel; dateTaken = $dateTaken; device = $device; software = $software; mtime = $_.LastWriteTime.ToString("s") })
  }

$csv = Join-Path $StateDir ("exif_{0}.csv" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$rows | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
$poveri = @($rows | Where-Object { -not $_.dateTaken }).Count
Write-Output ("=== EXIF === Immagini: {0} · senza data EXIF (candidati vision): {1}" -f $rows.Count, $poveri)
Write-Output "CSV: $csv"

