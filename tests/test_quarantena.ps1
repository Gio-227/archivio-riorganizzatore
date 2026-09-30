<#
  test_quarantena.ps1 -- collaudo di execute.ps1 / undo.ps1 (v1.3-beta) su una cartella temporanea:
  ELIMINA = quarantena, validazione senza radice di quarantena, dry-run Cestino su disco fisso,
  reale + undo con ripristino esatto. Nomi con apostrofi. Esce con codice 1 se un controllo fallisce.
  Uso: powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_quarantena.ps1 -S archivio-riorganizzatore\scripts
#>
param([Parameter(Mandatory)][string]$S)
$ErrorActionPreference = 'Stop'
$S = (Resolve-Path -LiteralPath $S).Path
$T = Join-Path $env:TEMP ("riorg_qtest_" + (Get-Date -Format 'HHmmssfff'))
$st = Join-Path $T '_state'; $root = Join-Path $T 'dati'
New-Item -ItemType Directory -Force -Path "$root\sub dell'anno", $st | Out-Null
'a' | Set-Content -LiteralPath "$root\uno.txt"; 'b' | Set-Content -LiteralPath "$root\sub dell'anno\due d'oro.txt"; 'c' | Set-Content -LiteralPath "$root\tre.txt"
$before = Get-ChildItem -LiteralPath $root -Recurse -Force | ForEach-Object { $_.FullName.Substring($root.Length) } | Sort-Object
$ops = @(
  @{ tipo='ELIMINA'; da="$root\uno.txt" },
  @{ tipo='ELIMINA'; da="$root\sub dell'anno\due d'oro.txt" },
  @{ tipo='SPOSTA';  da="$root\tre.txt"; a="$root\sub dell'anno\tre.txt" }
)
$of = Join-Path $st 'ops.json'; $ops | ConvertTo-Json | Set-Content -LiteralPath $of -Encoding UTF8
$res = [ordered]@{}
$o1 = & "$S\execute.ps1" -OpsFile $of -StateDir $st -DryRun $true 3>&1 | ForEach-Object { "$_" }
$res['dryrun_senza_quarantena_da_WARN'] = [bool]($o1 -match 'VALIDAZIONE: 2 WARN')
$o2 = & "$S\execute.ps1" -OpsFile $of -StateDir $st -DryRun $true -DeleteMode Cestino 3>&1 | ForEach-Object { "$_" }
$res['dryrun_cestino_su_disco_fisso_0_WARN'] = [bool]($o2 -match 'VALIDAZIONE: 0 WARN')
$o3 = & "$S\execute.ps1" -OpsFile $of -StateDir $st -DryRun $true -QuarantineRoot $root 3>&1 | ForEach-Object { "$_" }
$res['dryrun_quarantena_0_WARN'] = [bool]($o3 -match 'VALIDAZIONE: 0 WARN')
& "$S\execute.ps1" -OpsFile $of -StateDir $st -DryRun $false -QuarantineRoot $root | Out-Null
$q = @(Get-ChildItem -LiteralPath "$root\_DA_ELIMINARE" -Recurse -File -Force)
$res['reale_due_file_in_quarantena'] = ($q.Count -eq 2) -and -not (Test-Path -LiteralPath "$root\uno.txt")
& "$S\undo.ps1" -StateDir $st -DryRun $false | Out-Null
$after = Get-ChildItem -LiteralPath $root -Recurse -Force | ForEach-Object { $_.FullName.Substring($root.Length) } | Sort-Object
$res['undo_ripristino_esatto'] = ($null -eq (Compare-Object $before $after))
$res['undo_quarantena_rimossa'] = -not (Test-Path -LiteralPath "$root\_DA_ELIMINARE")
Remove-Item -LiteralPath $T -Recurse -Force
$fail = 0
foreach ($k in $res.Keys) { $v = $res[$k]; if (-not $v) { $fail++ }; "{0,-40} {1}" -f $k, $(if ($v) { 'PASS' } else { 'FAIL' }) }
"ESITO: {0}/{1}" -f ($res.Count - $fail), $res.Count
if ($fail) { exit 1 }
