#!/usr/bin/env python3
"""Controlli statici del pacchetto skill: frontmatter, file citati, pre-flight dell'albero. Solo libreria standard."""
import os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archivio-riorganizzatore")
errors = []
skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
if not m:
    errors.append("SKILL.md: frontmatter YAML assente")
else:
    fm = m.group(1)
    name = re.search(r'^name:\s*"?([^"\n]+)"?', fm, re.M)
    desc = re.search(r'^description:\s*(.+)$', fm, re.M)
    if not name or name.group(1).strip() != os.path.basename(os.path.normpath(ROOT)):
        errors.append("frontmatter: 'name' deve coincidere con il nome della cartella")
    if not desc or len(desc.group(1)) > 1100:
        errors.append("frontmatter: 'description' assente o troppo lunga")
for ref in sorted(set(re.findall(r"`((?:references|scripts|assets)/[\w./-]+\.(?:md|ps1|py|html))`", skill))):
    if not os.path.exists(os.path.join(ROOT, ref)):
        errors.append("SKILL.md cita un file che non esiste: " + ref)
alb = open(os.path.join(ROOT, "scripts", "albero.ps1"), encoding="utf-8-sig").read()
on = set(re.findall(r"onclick=['\"]?([A-Za-z_]\w*)\(", alb))
fn = set(re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", alb))
if re.search(r"(function\s+all\(|onclick=['\"]?all\()", alb):
    errors.append("albero.ps1: handler 'all(' non prefissato (bug #23)")
if on - fn:
    errors.append("albero.ps1: handler senza funzione: %s" % sorted(on - fn))
if any(not x.startswith("ax") for x in on):
    errors.append("albero.ps1: handler senza prefisso ax: %s" % sorted(x for x in on if not x.startswith("ax")))
for e in errors:
    print("FAIL " + e)
print("validate_skill: %s" % ("OK" if not errors else "%d errori" % len(errors)))
sys.exit(1 if errors else 0)
