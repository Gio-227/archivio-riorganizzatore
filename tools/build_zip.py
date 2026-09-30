#!/usr/bin/env python3
"""Ricostruisce dist/archivio-riorganizzatore_v<versione>.zip, pronto da caricare in Claude (Customize -> Skills).
Deterministico: ordine fisso e date fisse, cosi' lo stesso sorgente da' lo stesso zip."""
import os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
SKILL = "archivio-riorganizzatore"
ver = re.search(r'VERSION = "([^"]+)"', open(os.path.join(REPO, SKILL, "scripts", "riorg.py"), encoding="utf-8").read()).group(1)
short = ver.replace(".0-beta", "-beta")
out = os.path.join(REPO, "dist", "%s_v%s.zip" % (SKILL, short))
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(os.path.join(REPO, SKILL)):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for f in sorted(files):
            if f.endswith((".pyc", ".DS_Store")):
                continue
            p = os.path.join(root, f)
            arc = os.path.relpath(p, REPO).replace(os.sep, "/")
            zi = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(p, "rb") as fh:
                z.writestr(zi, fh.read())
print("zip: %s (%d byte)" % (out, os.path.getsize(out)))
