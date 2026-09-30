<#
.SYNOPSIS
  albero.ps1 -- DEBRIEF ALBERO (Fase 4, obbligatorio). Genera l'albero completo interattivo della
  cartella riorganizzata: annidamenti aperti, chevron cliccabili, commento per ogni riga
  (tag Nota/Sposta/Ripristina/Elimina) e bottone "Esporta risposte".
.PARAMETER Target  Cartella da rappresentare.
.PARAMETER Out     Percorso HTML di output (tenerlo in A\_riorg, mai in archivio).
.PARAMETER Title   Titolo in testata (default: nome della cartella).
.NOTES
  Eseguire lato Windows/PowerShell: dopo gli spostamenti il mount bash puo essere stantio.
#>
param(
  [Parameter(Mandatory)][string]$Target,
  [Parameter(Mandatory)][string]$Out,
  [string]$Title = ""
)
$ErrorActionPreference='Stop'
if(-not $Title){ $Title = Split-Path $Target -Leaf }
$FOLD="<svg viewBox='0 0 24 24' width='15' height='15'><path fill='#e0a92e' d='M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8z'/></svg>"
$FILE="<svg viewBox='0 0 24 24' width='14' height='14'><path fill='#8a8f98' d='M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z'/><path fill='#5b6069' d='M14 2l6 6h-6z'/></svg>"
function Enc($s){ $s -replace '&','&amp;' -replace '<','&lt;' -replace '>','&gt;' }
function EncA($s){ (Enc $s) -replace "'","&#39;" -replace '"','&quot;' }
$rows = New-Object System.Collections.Generic.List[string]
$script:nd=0; $script:nf=0
function Emit($dir,$depth){
  # fix P3: -EA SilentlyContinue -- con $ErrorActionPreference=Stop una dir illeggibile uccideva l'albero intero.
  # NB: i commenti vivono in localStorage con chiave=path: dopo spostamenti/rinomina diventano stale nell'export.
  $items = Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue | Sort-Object @{Expression={ -not $_.PSIsContainer }}, Name
  foreach($it in $items){
    $pad = 8 + $depth*20; $name = Enc $it.Name; $pa = EncA $it.FullName
    if($it.PSIsContainer){
      $script:nd++
      $cnt = @(Get-ChildItem -LiteralPath $it.FullName -Force -ErrorAction SilentlyContinue).Count
      $rows.Add("<div class='node'><div class='r d' data-path='$pa' style='padding-left:${pad}px'><span class='cv' onclick='axtg(this)'>&#9662;</span>$FOLD<span class='nm'>$name</span><span class='ct'>$cnt</span><button class='cm' onclick='axnote(this)' title='Commenta'>&#128172;</button></div><div class='children'>")
      Emit $it.FullName ($depth+1)
      $rows.Add("</div></div>")
    } else {
      $script:nf++
      $rows.Add("<div class='r f' data-path='$pa' style='padding-left:${pad}px'><span class='cv'>&nbsp;</span>$FILE<span class='nm'>$name</span><button class='cm' onclick='axnote(this)' title='Commenta'>&#128172;</button></div>")
    }
  }
}
Emit $Target 0
$ts = Get-Date -Format 'yyyy-MM-dd HH:mm'
$head = @"
<!-- Header Cowork v1.0 | albero debrief (skill archivio v1.2) | $ts CEST -->
<!DOCTYPE html><html lang='it'><head><meta charset='UTF-8'><title>$Title - albero verifica</title><style>
body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px/1.55 'Segoe UI',system-ui,sans-serif}
.top{position:sticky;top:0;background:#252526;border-bottom:1px solid #333;padding:12px 16px;z-index:5;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.top h1{margin:0;font-size:15px;color:#e0a92e;font-weight:600}
.top .s{color:#8a8f98;font-size:12px}
.btn{background:#333;border:1px solid #444;color:#d4d4d4;font-size:11px;padding:5px 11px;border-radius:6px;cursor:pointer}
.btn:hover{background:#3d3d3d}.btn.exp{background:#e0a92e;color:#1e1e1e;border-color:#e0a92e;font-weight:600}
.tree{padding:8px 0 60px}
.r{display:flex;align-items:center;gap:6px;height:23px;white-space:nowrap;border-radius:3px}
.r:hover{background:#2a2d2e}
.cv{width:12px;color:#c5c5c5;font-size:11px;flex:0 0 auto;text-align:center;transition:transform .1s;cursor:pointer}
.r.f .cv{cursor:default}
.node.collapsed>.children{display:none}.node.collapsed>.r .cv{transform:rotate(-90deg)}
.nm{flex:1;overflow:hidden;text-overflow:ellipsis}.d>.nm{color:#e8e8e8}.f>.nm{color:#b7bcc4}
.ct{color:#6a6f78;font-size:11px;flex:0 0 auto}
.cm{opacity:0;background:none;border:0;color:#8a8f98;cursor:pointer;font-size:12px;padding:0 8px;flex:0 0 auto}
.r:hover .cm{opacity:.85}.cm:hover{color:#e0a92e}
.r.has-c{background:#2b2620}.r.has-c .cm{opacity:1;color:#e0a92e}
.cmt-badge{font-size:10px;padding:1px 7px;border-radius:8px;flex:0 0 auto;color:#1e1e1e;margin-right:4px}
.t-Nota{background:#c5c5c5}.t-Sposta{background:#8ab0db}.t-Ripristina{background:#83c994}.t-Elimina{background:#dc9690}
.cmt-edit{background:#2a2a2d;border:1px solid #3a3a40;border-radius:8px;margin:2px 12px 6px 40px;padding:8px}
.cmt-edit .tags{display:flex;gap:4px;margin-bottom:6px}
.tg-b{background:#333;border:1px solid #444;color:#c9c9d0;font-size:10.5px;padding:2px 9px;border-radius:12px;cursor:pointer}
.tg-b.on{background:#e0a92e;color:#1e1e1e;border-color:#e0a92e}
.cmt-edit textarea{width:100%;box-sizing:border-box;background:#1b1b1e;border:1px solid #3a3a40;color:#d4d4d4;border-radius:6px;padding:6px;font:12px 'Segoe UI',sans-serif;min-height:40px;resize:vertical}
.ed-a{margin-top:6px;display:flex;gap:6px}
.sv{background:#83c994;color:#14210b;border:0;padding:4px 13px;border-radius:6px;cursor:pointer;font-size:11.5px;font-weight:600}
.dl{background:#3a3a40;color:#c9c9d0;border:0;padding:4px 13px;border-radius:6px;cursor:pointer;font-size:11.5px}
svg{flex:0 0 auto;vertical-align:middle}
#expWrap{display:none;position:sticky;bottom:0;background:#252526;border-top:1px solid #3a3a40;padding:10px 16px;z-index:5}
#exp{width:100%;box-sizing:border-box;height:120px;background:#1b1b1e;color:#d4d4d4;border:1px solid #3a3a40;border-radius:6px;padding:8px;font:11.5px ui-monospace,monospace}
.expr{display:flex;gap:8px;margin-top:6px;align-items:center}
</style></head><body>
<div class='top'><h1>&#128193; $Title &mdash; verifica</h1>
<span class='s'>$($script:nd) cartelle &middot; $($script:nf) file &middot; $ts</span><span style='flex:1'></span>
<button class='btn' onclick='axSetAll(false)'>Espandi</button><button class='btn' onclick='axSetAll(true)'>Collassa</button>
<button class='btn exp' onclick='axexportC()'>Esporta risposte</button></div>
<div class='tree'>
"@
$js = @'

<div id='expWrap'><textarea id='exp' readonly></textarea>
<div class='expr'><button class='sv' onclick='axcopyExp()'>Copia</button><button class='dl' onclick='axdlExp()'>Scarica .md</button><span class='s' id='expInfo'></span></div></div>
<script>
var LS='albero_comments_'+location.pathname;
function getC(){ try{return JSON.parse(localStorage.getItem(LS)||'{}')}catch(e){return {}} }
function setC(o){ try{localStorage.setItem(LS,JSON.stringify(o))}catch(e){} }
function axtg(el){ var n=el.closest('.node'); if(n) n.classList.toggle('collapsed'); }
function axSetAll(c){ document.querySelectorAll('.node').forEach(function(n){ c?n.classList.add('collapsed'):n.classList.remove('collapsed'); }); }
function markRow(row,tag){ var b=row.querySelector('.cmt-badge'); if(b) b.remove(); row.classList.remove('has-c'); if(tag){ row.classList.add('has-c'); var s=document.createElement('span'); s.className='cmt-badge t-'+tag; s.textContent=tag; row.insertBefore(s,row.querySelector('.cm')); } }
function axnote(btn){
  var row=btn.closest('.r'), path=row.getAttribute('data-path'), nx=row.nextElementSibling;
  if(nx && nx.classList.contains('cmt-edit')){ nx.remove(); return; }
  document.querySelectorAll('.cmt-edit').forEach(function(e){e.remove();});
  var c=getC()[path]||{tag:'Nota',text:''}, tags=['Nota','Sposta','Ripristina','Elimina'], th='';
  tags.forEach(function(t){ th+="<button class='tg-b"+(c.tag===t?' on':'')+"' onclick='axsetTag(this)'>"+t+"</button>"; });
  var ed=document.createElement('div'); ed.className='cmt-edit';
  ed.innerHTML="<div class='tags'>"+th+"</div><textarea placeholder='Commento, correzione o richiesta di ripristino...'></textarea><div class='ed-a'><button class='sv' onclick='axsaveNote(this)'>Salva</button><button class='dl' onclick='axdelNote(this)'>Rimuovi</button></div>";
  row.parentNode.insertBefore(ed,row.nextSibling);
  ed.querySelector('textarea').value=c.text||''; ed.querySelector('textarea').focus();
}
function axsetTag(b){ b.parentNode.querySelectorAll('.tg-b').forEach(function(x){x.classList.remove('on');}); b.classList.add('on'); }
function axsaveNote(b){ var ed=b.closest('.cmt-edit'), row=ed.previousElementSibling, path=row.getAttribute('data-path');
  var on=ed.querySelector('.tg-b.on'), tag=on?on.textContent:'Nota', text=ed.querySelector('textarea').value.trim();
  var o=getC(); o[path]={tag:tag,text:text}; setC(o); markRow(row,tag); ed.remove(); }
function axdelNote(b){ var ed=b.closest('.cmt-edit'), row=ed.previousElementSibling, path=row.getAttribute('data-path');
  var o=getC(); delete o[path]; setC(o); markRow(row,null); ed.remove(); }
function axexportC(){
  var o=getC(), keys=Object.keys(o), w=document.getElementById('expWrap'), ta=document.getElementById('exp');
  var out='# Risposte verifica albero - '+new Date().toLocaleString('it-IT')+'\n\n';
  if(!keys.length){ out+='(nessun commento inserito)\n'; } else { keys.sort().forEach(function(p){ var c=o[p]; out+='- ['+c.tag+'] '+p+(c.text?(' -- '+c.text):'')+'\n'; }); }
  ta.value=out; w.style.display='block'; document.getElementById('expInfo').textContent=keys.length+' righe commentate'; ta.focus(); ta.select();
}
function axcopyExp(){ var ta=document.getElementById('exp'); ta.select(); try{document.execCommand('copy');}catch(e){} }
function axdlExp(){ var ta=document.getElementById('exp'); var bl=new Blob([ta.value],{type:'text/markdown'}); var a=document.createElement('a'); a.href=URL.createObjectURL(bl); a.download='risposte_albero.md'; a.click(); }
(function(){ var o=getC(); document.querySelectorAll('.r').forEach(function(r){ var p=r.getAttribute('data-path'); if(o[p]) markRow(r,o[p].tag); }); })();
</script>
'@
$html = $head + ($rows -join "`r`n") + "`r`n</div>" + $js + "</body></html>"
$dir = Split-Path $Out -Parent
if($dir -and -not (Test-Path -LiteralPath $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
[System.IO.File]::WriteAllText($Out, $html, [System.Text.Encoding]::UTF8)
Write-Output ("Albero generato: {0}  ({1} cartelle, {2} file)" -f $Out,$script:nd,$script:nf)
