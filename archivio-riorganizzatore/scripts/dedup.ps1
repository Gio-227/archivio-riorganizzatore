<#
.SYNOPSIS
  dedup.ps1 — Fase 2: dedup gated. MD5 solo sui candidati per dimensione, scritti in cache.
.DESCRIPTION
  Raggruppa i file per dimensione; calcola MD5 SOLO per i gruppi con piu' di un file
  (leva: mai hash su tutti). Aggiorna md5 in riorg_cache.json e stampa i gruppi di duplicati.
  PowerShell 5.1+.
.PARAMETER Target    Cartella analizzata (stessa di scan.ps1).
.PARAMETER StateDir  Cartella di stato del progetto. Default: cartella corrente.
.PARAMETER ExcludeProtected  Default $true: salta le entry dentro zone protette
  (.git, node_modules), anche se presenti in una cache generata prima del fix B2.
#>
param(
  [Parameter(Mandatory)] [string] $Target,
  [string] $StateDir = ".",
  [bool] $ExcludeProtected = $true
)
$ErrorActionPreference = "Stop"
$cachePath = Join-Path $StateDir "riorg_cache.json"
if (-not (Test-Path -LiteralPath $cachePath)) { throw "Cache assente: esegui prima scan.ps1." }

$j = Get-Content -LiteralPath $cachePath -Raw -Encoding UTF8 | ConvertFrom-Json
$cache = @{}
foreach ($p in $j.files.PSObject.Properties) { $cache[$p.Name] = $p.Value }

# Entry eleggibili: fuori dalle zone protette (bug B2; copre anche cache pre-fix)
$protectedRx = '(^|\\)(\.git|node_modules)(\\|$)'
$eligible = $cache.GetEnumerator() | Where-Object { (-not $ExcludeProtected -or $_.Key -notmatch $protectedRx) -and [long]$_.Value.size -gt 0 }   # v1.3-beta: i file vuoti non sono doppioni (erano un falso gruppo)

# Gruppi candidati: stessa dimensione, >1 file
$bySize = $eligible | Group-Object { $_.Value.size } | Where-Object Count -gt 1
$groups = New-Object System.Collections.Generic.List[object]
foreach ($g in $bySize) {
  foreach ($e in $g.Group) {
    $rel = $e.Key
    if (-not $e.Value.md5) {                              # calcola solo se non gia' in cache
      $full = Join-Path $Target $rel
      if (Test-Path -LiteralPath $full) {
        $e.Value.md5 = (Get-FileHash -LiteralPath $full -Algorithm MD5).Hash
      }
    }
  }
}
# Raggruppa per MD5 i candidati (solo eleggibili)
$dups = ($eligible | Where-Object { $_.Value.md5 } |
  Group-Object { $_.Value.md5 } | Where-Object Count -gt 1)

@{ schema = 1; scan_ts = $j.scan_ts; files = $cache } |
  ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $cachePath -Encoding UTF8

Write-Output ("=== DEDUP === Gruppi duplicati: {0}" -f @($dups).Count)   # fix P2: @() -- con 1 solo gruppo .Count contava le copie
foreach ($d in $dups) {
  Write-Output ("MD5 {0} ({1} copie):" -f $d.Name.Substring(0,8), $d.Count)
  $d.Group | ForEach-Object { "   $($_.Key)" }
}
Write-Output ("Hash calcolati in questa run: solo candidati per dimensione (mai su tutti i file).")

