<#
.SYNOPSIS
  undo.ps1 -- annulla una run leggendo il journal strutturato, in ordine LIFO.
.DESCRIPTION
  v1.2.1 (fix P0). L'inversa e' DERIVATA dai campi { tipo, da, a } del journal ed eseguita
  con cmdlet diretti e -LiteralPath: NIENTE Invoke-Expression, quindi nessuna rottura su
  path con apostrofi (L', Sant', dell'...) e nessuna injection possibile.
  - SPOSTA / RINOMINA -> Move-Item -LiteralPath a -> da (con guardie: 'a' deve esistere,
    'da' non deve gia' esistere).
  - CREA -> Remove-Item su 'a' SOLO se la cartella esiste ed e' VUOTA; mai -Recurse cieco.
  - ELIMINA in quarantena (v1.3-beta, nota 'quarantena') -> riporta 'a' -> 'da', poi toglie le cartelle
    di quarantena rimaste vuote. ELIMINA via Cestino -> manuale.
  - MERGE / FLATTEN -> segnalate per intervento manuale.
  Legge journal schema 2 (v1.2.1) e, in compatibilita', schema 1 (v<=1.2.0: usa i campi
  tipo/da/a ignorando la stringa 'inversa'). PowerShell 5.1+.
.PARAMETER StateDir  Cartella di stato del progetto. Default: cartella corrente.
.PARAMETER Journal   Journal specifico (es. riorg_undo_run_20260721_030000.json).
                     Default: riorg_undo.json = ultima run.
.PARAMETER DryRun    Default $true: mostra le inverse senza eseguirle.
#>
param(
  [string] $StateDir = ".",
  [string] $Journal = "",
  [bool] $DryRun = $true
)
$ErrorActionPreference = "Stop"
$undoPath = if ($Journal) { if (Test-Path -LiteralPath $Journal) { $Journal } else { Join-Path $StateDir $Journal } } else { Join-Path $StateDir "riorg_undo.json" }
if (-not (Test-Path -LiteralPath $undoPath)) { throw "Undo journal assente: $undoPath" }

$j = Get-Content -LiteralPath $undoPath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Output ("=== UNDO run {0} -- {1} op -- LIFO ===" -f $j.run_id, @($j.ops).Count)
$rev = @($j.ops); [array]::Reverse($rev)
$ok=0; $skip=0; $man=0
foreach ($op in $rev) {
  $tag = if ($DryRun) { "[DRY]" } else { "[REALE]" }
  switch ($op.tipo) {
    { $_ -in @("SPOSTA","RINOMINA") } {
      Write-Output ("{0} undo #{1} {2}: '{3}' <- '{4}'" -f $tag, $op.n, $op.tipo, $op.da, $op.a)
      if (-not $DryRun) {
        if (-not (Test-Path -LiteralPath $op.a)) { Write-Warning "Salto #$($op.n): '$($op.a)' non esiste piu'."; $skip++; break }
        if (Test-Path -LiteralPath $op.da) { Write-Warning "Salto #$($op.n): '$($op.da)' esiste gia' (collisione)."; $skip++; break }
        try { Move-Item -LiteralPath $op.a -Destination $op.da -ErrorAction Stop; $ok++ }
        catch { Write-Warning "Fallita inversa #$($op.n): $_"; $skip++ }
      }
    }
    "ELIMINA" {
      if ($op.nota -ne "quarantena") { Write-Warning ("Op #{0} ELIMINA via Cestino: ripristino manuale dal Cestino." -f $op.n); $man++; break }
      Write-Output ("{0} undo #{1} ELIMINA (quarantena): '{2}' <- '{3}'" -f $tag, $op.n, $op.da, $op.a)
      if (-not $DryRun) {
        if (-not (Test-Path -LiteralPath $op.a)) { Write-Warning "Salto #$($op.n): '$($op.a)' non e' piu' in quarantena."; $skip++; break }
        if (Test-Path -LiteralPath $op.da) { Write-Warning "Salto #$($op.n): '$($op.da)' esiste gia' (collisione)."; $skip++; break }
        try {
          $pd = Split-Path $op.da -Parent; if (-not (Test-Path -LiteralPath $pd)) { New-Item -ItemType Directory -Force -Path $pd | Out-Null }
          Move-Item -LiteralPath $op.a -Destination $op.da -ErrorAction Stop; $ok++
          $d = Split-Path $op.a -Parent
          while ($d -and ($d -match '\\_DA_ELIMINARE(\\|$)') -and (Test-Path -LiteralPath $d) -and @(Get-ChildItem -LiteralPath $d -Force).Count -eq 0) {
            Remove-Item -LiteralPath $d -Force; if ((Split-Path $d -Leaf) -eq "_DA_ELIMINARE") { break }; $d = Split-Path $d -Parent
          }
        } catch { Write-Warning "Fallita inversa #$($op.n): $_"; $skip++ }
      }
    }
    "CREA" {
      Write-Output ("{0} undo #{1} CREA: rimuovi '{2}' solo se vuota" -f $tag, $op.n, $op.a)
      if (-not $DryRun) {
        if (-not (Test-Path -LiteralPath $op.a)) { $skip++; break }
        if (@(Get-ChildItem -LiteralPath $op.a -Force -ErrorAction SilentlyContinue).Count -eq 0) {
          try { Remove-Item -LiteralPath $op.a -Force -ErrorAction Stop; $ok++ }
          catch { Write-Warning "Fallita inversa #$($op.n): $_"; $skip++ }
        } else { Write-Warning "Salto #$($op.n): '$($op.a)' NON vuota -- mai rimozione ricorsiva cieca (fix P0)."; $skip++ }
      }
    }
    default {
      Write-Warning ("Op #{0} ({1}) non auto-invertibile: intervento manuale{2}." -f $op.n, $op.tipo, $(if($op.tipo -eq 'ELIMINA'){' (ripristino dal Cestino)'}else{''}))
      $man++
    }
  }
}
if ($DryRun) { Write-Output "DRY-RUN undo: nessuna modifica. Rilancia con -DryRun:`$false." }
else { Write-Output ("UNDO completato: {0} ok, {1} saltate, {2} manuali." -f $ok, $skip, $man) }
