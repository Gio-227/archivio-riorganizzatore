<#
.SYNOPSIS
  execute.ps1 -- Fase 3: esegue le operazioni approvate. Dry-run validante di default.
  Undo journal STRUTTURATO per run, scritto PRIMA di ogni operazione. ELIMINA solo via Cestino.
.DESCRIPTION
  v1.3-beta: ELIMINA = QUARANTENA di default (sposta in <QuarantineRoot>\_DA_ELIMINARE\<run_id>\...
  sullo stesso volume, invertibile da undo.ps1). Il Cestino resta solo come -DeleteMode Cestino e
  solo su dischi locali fissi: sulle unita' di rete e rimovibili il Cestino di Windows non esiste
  e l'eliminazione sarebbe definitiva.
  v1.2.1. Legge una lista JSON di operazioni { tipo, da, a } e le esegue nell'ordine canonico
  CREA -> SPOSTA -> RINOMINA -> MERGE -> FLATTEN -> ELIMINA; a parita' di tipo vale l'ordine
  del file (campo seq assegnato all'ingresso: Sort-Object stabile composito, fix P1).
  Il journal e' per-run: riorg_undo_<run_id>.json + copia come riorg_undo.json "ultima run"
  (fix P2 -- le run successive non sovrascrivono piu' la storia). Ogni op registra SOLO dati
  strutturati (n, seq, tipo, da, a): l'inversa la costruisce undo.ps1, niente stringhe di
  comando nel journal, niente Invoke-Expression (fix P0 -- apostrofi/injection).
  Dry-run VALIDANTE (fix P1): Test-Path su ogni sorgente + collisioni sulle destinazioni
  -> WARN; con WARN>0 fermati e mostra i problemi prima del reale.

  AMBIENTE: eseguire FUORI dal mount Cowork (bug #18: handle aperti -> Access denied sui
  folder; i file singoli passano). In dubbio: verifica con un test su cartella sacrificabile
  invece di assumere il blocco. Fallback imperfetto: -AllowContentMove. PowerShell 5.1+.
.PARAMETER OpsFile          JSON con le operazioni approvate dal widget.
.PARAMETER StateDir         Cartella di stato del progetto. Default: cartella corrente.
.PARAMETER DryRun           Default $true: valida e simula senza scrivere. -DryRun:$false per il reale.
.PARAMETER AllowContentMove Fallback content-move su Access denied (target montato). Default $false.
.PARAMETER QuarantineRoot   Radice della quarantena (stesso volume dei file da eliminare). Obbligatoria se ci sono ELIMINA.
.PARAMETER DeleteMode       Quarantena (default) | Cestino (solo dischi locali fissi).
#>
param(
  [Parameter(Mandatory)] [string] $OpsFile,
  [string] $StateDir = ".",
  [bool] $DryRun = $true,
  [bool] $AllowContentMove = $false,
  [string] $QuarantineRoot = "",
  [ValidateSet("Quarantena","Cestino")] [string] $DeleteMode = "Quarantena"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName Microsoft.VisualBasic

$runId    = "run_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")
$undoRun  = Join-Path $StateDir ("riorg_undo_{0}.json" -f $runId)
$undoLast = Join-Path $StateDir "riorg_undo.json"
$ops = Get-Content -LiteralPath $OpsFile -Raw -Encoding UTF8 | ConvertFrom-Json
$script:journal = [ordered]@{ schema = 2; run_id = $runId; ts = (Get-Date).ToString("s"); ops = @() }

function Save-Journal {
  $json = $script:journal | ConvertTo-Json -Depth 6
  Set-Content -LiteralPath $undoRun  -Value $json -Encoding UTF8   # journal della run (storico)
  Set-Content -LiteralPath $undoLast -Value $json -Encoding UTF8   # "ultima run" per undo.ps1
}

function Move-PathRobust([string]$src, [string]$dst, [bool]$allowContent) {
  try {
    Move-Item -LiteralPath $src -Destination $dst -ErrorAction Stop
  } catch [System.UnauthorizedAccessException] {
    if (-not $allowContent) {
      throw ("Access denied su '{0}'. Probabile target MONTATO in Cowork (handle aperti sulle directory). Esegui FUORI MOUNT, oppure rilancia con -AllowContentMove." -f $src)
    }
    if (Test-Path -LiteralPath $src -PathType Container) {
      New-Item -ItemType Directory -Force -Path $dst | Out-Null
      Get-ChildItem -LiteralPath $src -Force | ForEach-Object {
        Move-PathRobust $_.FullName (Join-Path $dst $_.Name) $true
      }
      try { Remove-Item -LiteralPath $src -Force -ErrorAction Stop }
      catch { Write-Warning ("Cartella sorgente svuotata ma non rimovibile (handle tenuto): '{0}' -- rimuovila a mount libero." -f $src) }
    } else { throw }
  }
}

function Remove-ToRecycle([string]$path) {
  if (Test-Path -LiteralPath $path -PathType Container) {
    [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($path, 'OnlyErrorDialogs', 'SendToRecycleBin')
  } else {
    [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($path, 'OnlyErrorDialogs', 'SendToRecycleBin')
  }
}

# --- ordinamento stabile: tipo canonico, poi seq di ingresso (fix P1) ---
$order = @{ CREA = 1; SPOSTA = 2; RINOMINA = 3; MERGE = 4; FLATTEN = 5; ELIMINA = 6 }
$seq = 0
$ops = $ops | ForEach-Object { $seq++; $_ | Add-Member -NotePropertyName seq -NotePropertyValue $seq -PassThru -Force }
$sorted = $ops | Sort-Object @{Expression={ $order[$_.tipo] }}, @{Expression={ $_.seq }}

# --- v1.3-beta: destinazione in quarantena per ogni ELIMINA (calcolata sempre, dry-run e reale) ---
$qwarn = New-Object System.Collections.Generic.List[string]
foreach ($op in $sorted) {
  if ($op.tipo -ne "ELIMINA") { continue }
  $src = [string]$op.da
  if ($DeleteMode -eq "Cestino") {
    $root = [System.IO.Path]::GetPathRoot($src)
    $fixed = $false
    try { $fixed = (-not $root.StartsWith("\\")) -and ([System.IO.DriveInfo]::new($root).DriveType -eq "Fixed") } catch { }
    if (-not $fixed) { $qwarn.Add(("[VALIDA] Cestino non garantito su '{0}' (unita' di rete o rimovibile): usa -DeleteMode Quarantena (seq {1})" -f $root, $op.seq)) }
    continue
  }
  if (-not $QuarantineRoot) { $qwarn.Add(("[VALIDA] ELIMINA senza -QuarantineRoot (seq {0})" -f $op.seq)); continue }
  $qr = [System.IO.Path]::GetFullPath($QuarantineRoot)
  if ([System.IO.Path]::GetPathRoot($src).ToLower() -ne [System.IO.Path]::GetPathRoot($qr).ToLower()) {
    $qwarn.Add(("[VALIDA] quarantena su un volume diverso da '{0}' (seq {1})" -f $src, $op.seq)); continue
  }
  $full = [System.IO.Path]::GetFullPath($src)
  $rel = if ($full.ToLower().StartsWith($qr.TrimEnd('\').ToLower() + "\")) { $full.Substring($qr.TrimEnd('\').Length + 1) } else { Split-Path $full -Leaf }
  $dest = Join-Path (Join-Path (Join-Path $qr "_DA_ELIMINARE") $runId) $rel
  if (Test-Path -LiteralPath $dest) { $qwarn.Add(("[VALIDA] in quarantena esiste gia': {0} (seq {1})" -f $dest, $op.seq)) }
  $op | Add-Member -NotePropertyName a -NotePropertyValue $dest -Force
}
if ($qwarn.Count -gt 0 -and -not $DryRun) { $qwarn | ForEach-Object { Write-Warning $_ }; throw ("{0} WARN sulla quarantena: esecuzione reale rifiutata." -f $qwarn.Count) }

# --- dry-run validante (fix P1): sorgenti esistenti + collisioni destinazione ---
if ($DryRun) {
  $warn = 0
  foreach ($w in $qwarn) { Write-Warning $w; $warn++ }
  foreach ($op in $sorted) {
    if ($op.tipo -ne "CREA" -and $op.da) {
      if (-not (Test-Path -LiteralPath $op.da)) { Write-Warning ("[VALIDA] sorgente assente: {0} ({1} seq {2})" -f $op.da, $op.tipo, $op.seq); $warn++ }
    }
    if ($op.tipo -in @("SPOSTA","RINOMINA") -and $op.a) {
      if (Test-Path -LiteralPath $op.a) { Write-Warning ("[VALIDA] destinazione gia' esistente (rischio annidamento): {0} ({1} seq {2})" -f $op.a, $op.tipo, $op.seq); $warn++ }
    }
  }
  if ($warn -gt 0) { Write-Output ("VALIDAZIONE: {0} WARN -- risolvi prima del reale." -f $warn) }
  else { Write-Output "VALIDAZIONE: 0 WARN." }
}

$n = 0
foreach ($op in $sorted) {
  $n++
  $tag = if ($DryRun) { "[DRY]" } else { "[REALE]" }
  $nota = $null
  switch ($op.tipo) {
    "CREA"     { $act = { New-Item -ItemType Directory -Force -Path $op.a | Out-Null } }
    "SPOSTA"   { $act = { Move-PathRobust $op.da $op.a $AllowContentMove } }
    "RINOMINA" { $act = { Move-PathRobust $op.da $op.a $AllowContentMove } }
    "MERGE"    { $nota = "non auto-invertibile: ricostruzione da report"; $act = { Get-ChildItem -LiteralPath $op.da -Force | Move-Item -Destination $op.a } }
    "FLATTEN"  { $nota = "non auto-invertibile: ricostruzione da report"; $act = { Get-ChildItem -LiteralPath $op.da -Recurse -File | Move-Item -Destination $op.a } }
    "ELIMINA"  {
      if ($DeleteMode -eq "Cestino") { $nota = "ripristino manuale dal Cestino"; $act = { Remove-ToRecycle $op.da } }
      else { $nota = "quarantena"; $act = { New-Item -ItemType Directory -Force -Path (Split-Path $op.a -Parent) | Out-Null; Move-PathRobust $op.da $op.a $AllowContentMove } }
    }
    default    { Write-Warning "Tipo sconosciuto: $($op.tipo)"; continue }
  }
  Write-Output ("{0} #{1} {2}: {3} -> {4}" -f $tag, $n, $op.tipo, $op.da, $op.a)
  if (-not $DryRun) {
    # journal PRIMA dell'azione -- SOLO dati strutturati (fix P0): l'inversa la deriva undo.ps1
    $entry = [ordered]@{ n = $n; seq = $op.seq; tipo = $op.tipo; da = "$($op.da)"; a = "$($op.a)" }
    if ($nota) { $entry.nota = $nota }
    $script:journal.ops += [pscustomobject]$entry
    Save-Journal
    & $act
  }
}
if ($DryRun) { Write-Output "DRY-RUN: nessuna scrittura. Rilancia con -DryRun:`$false per il reale." }
else { Write-Output ("Undo journal run: {0}`nUltima run: {1}" -f $undoRun, $undoLast) }
