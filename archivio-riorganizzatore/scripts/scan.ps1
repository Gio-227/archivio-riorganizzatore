<#
.SYNOPSIS
  scan.ps1 — Fase 2 (sola lettura): scansione strutturale + aggiornamento cache.
.DESCRIPTION
  Scansiona ricorsivamente -Target, scrive un CSV su disco e aggiorna riorg_cache.json
  (chiave path+mtime+size). Stampa un aggregato <=40 righe. Nessuna modifica ai file.
  Sostituisce il blocco scan inline (leva L2). PowerShell 5.1+.
.PARAMETER Target    Cartella da scansionare (percorso assoluto).
.PARAMETER StateDir  Cartella di stato del progetto (cache + CSV). Default: cartella corrente.
.PARAMETER NoCache   Invalida la cache e ricalcola tutto.
.PARAMETER ExcludeProtected  Default $true: esclude gli interni delle zone protette
  (.git, node_modules) da scan e cache (regola 11: blocchi-unita', mai gli interni).
  La presenza delle zone resta segnalata nell'aggregato. -ExcludeProtected:$false per includerle.
#>
param(
  [Parameter(Mandatory)] [string] $Target,
  [string] $StateDir = ".",
  [switch] $NoCache,
  [bool] $ExcludeProtected = $true
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Target)) { throw "Target non trovato: $Target" }

$cachePath = Join-Path $StateDir "riorg_cache.json"
$prev = @{}
if ((Test-Path -LiteralPath $cachePath) -and -not $NoCache) {
  try {
    $j = Get-Content -LiteralPath $cachePath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($p in $j.files.PSObject.Properties) { $prev[$p.Name] = $p.Value }
  } catch { Write-Warning "Cache illeggibile, ricalcolo." }
}

$protectedRx = '(^|\\)(\.git|node_modules)(\\|$)'   # zone protette (bug B2): interni esclusi
$files = Get-ChildItem -LiteralPath $Target -Recurse -File -Force
$protSkipped = 0
$protZones = @(Get-ChildItem -LiteralPath $Target -Recurse -Directory -Force |
  Where-Object { $_.Name -in '.git','node_modules' })
if ($ExcludeProtected) {
  $pre = @($files).Count
  $files = $files | Where-Object { $_.FullName.Substring($Target.Length) -notmatch $protectedRx }
  $protSkipped = $pre - @($files).Count
}
$rows  = New-Object System.Collections.Generic.List[object]
$cache = @{}
foreach ($f in $files) {
  $rel   = $f.FullName.Substring($Target.Length).TrimStart('\')
  $mtime = $f.LastWriteTime.ToString("s")
  $rows.Add([pscustomobject]@{ path = $rel; size = $f.Length; mtime = $mtime; ext = $f.Extension.ToLower() })
  $hit = $prev[$rel]
  if ($hit -and $hit.size -eq $f.Length -and $hit.mtime -eq $mtime) {
    $cache[$rel] = $hit                                   # HIT: riusa md5/classe senza I/O
  } else {
    $cache[$rel] = [pscustomobject]@{ size = $f.Length; mtime = $mtime; md5 = $null; classe = $null; conf = $null }
  }
}

$csv = Join-Path $StateDir ("scan_{0}.csv" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$rows | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
@{ schema = 1; scan_ts = (Get-Date).ToString("s"); files = $cache } |
  ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $cachePath -Encoding UTF8

# --- Aggregato <=40 righe ---
$emptyDirs = Get-ChildItem -LiteralPath $Target -Recurse -Directory -Force |
  Where-Object { (-not $ExcludeProtected -or $_.FullName.Substring($Target.Length) -notmatch $protectedRx) -and
                 @(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0 }
$dupCand = ($rows | Group-Object size | Where-Object Count -gt 1 |
  ForEach-Object { $_.Count } | Measure-Object -Sum).Sum
Write-Output "=== SCAN $Target ==="
Write-Output ("File totali: {0} · Dimensione: {1:N1} MB" -f $rows.Count, (($rows.size | Measure-Object -Sum).Sum / 1MB))
Write-Output ("Cartelle vuote: {0} · Candidati duplicati per dimensione: {1}" -f $emptyDirs.Count, [int]$dupCand)
if (@($protZones).Count -gt 0) {
  $zoneNote = if ($ExcludeProtected) { "interni ESCLUSI ({0} file saltati)" -f $protSkipped } else { "interni INCLUSI (-ExcludeProtected:`$false)" }
  Write-Output ("Zone protette (blocco-unita'): {0} -- {1}" -f @($protZones).Count, $zoneNote)
  $protZones | Select-Object -First 5 | ForEach-Object { "  [protetta] $($_.FullName.Substring($Target.Length).TrimStart('\'))" }
}
Write-Output "Per estensione (top 15):"
$rows | Group-Object ext | Sort-Object Count -Descending | Select-Object -First 15 |
  ForEach-Object { "  {0,-10} {1}" -f $_.Name, $_.Count }
Write-Output "CSV: $csv"
Write-Output "Cache: $cachePath"

