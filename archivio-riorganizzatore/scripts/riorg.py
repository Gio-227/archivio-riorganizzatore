#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
riorg.py -- motore multi-OS della skill archivio-riorganizzatore (v1.3-beta).
Solo libreria standard, Python >= 3.8. Gira su Windows, macOS e Linux.

Sottocomandi
  env      riconosce sistema, strumenti e volumi (sola lettura)
  scan     Fase 2: inventario + cache path+mtime+size + aggregato <=40 righe (sola lettura)
  dedup    Fase 2: MD5 solo sui candidati per dimensione, impronta rapida opzionale (sola lettura)
  dedup-multi  doppioni fra piu' radici (NAS, dischi) gia' scansionate, filtrabili con --only (sola lettura)
  execute  Fase 3: CREA / COPIA / SPOSTA / RINOMINA / ELIMINA(=quarantena). Dry-run di default.
  undo     riavvolge una run in ordine inverso, dal journal. Dry-run di default.
  albero   Fase 4: albero HTML di debrief (stesse funzioni di albero.ps1, prefisso ax) + --check
  bench    collaudo su cartella sintetica: correttezza + prestazioni, confrontabile fra sistemi

Regole che questo file rispetta (SKILL.md): dry-run prima del reale; journal scritto PRIMA di
ogni azione; nessuna cancellazione: ELIMINA sposta in quarantena sullo stesso volume; zone
protette mai smontate; ogni comando stampa il suo AUTOCONTROLLO e scrive una riga di metriche.
"""
import argparse, csv, datetime as dt, hashlib, html, json, os, platform, random, re, shutil, subprocess, sys, time

VERSION = "1.3.0-beta"
ENGINE = "riorg.py " + VERSION

# ---------------------------------------------------------------- costanti
PROTECTED_NAMES = {".git", "node_modules", ".svn", ".hg", "venv", ".venv", "__pycache__"}
PACKAGE_SUFFIXES = (".fcpbundle", ".photoslibrary", ".lrdata", ".app", ".imovielibrary", ".tvlibrary",
                    ".logicx", ".band", ".aplibrary", ".dvdmedia", ".rtfd", ".pages", ".numbers", ".key",
                    ".xcodeproj", ".bundle", ".framework", ".sparsebundle")
CARD_ROOTS = {"DCIM", "PRIVATE", "AVCHD", "BPAV", "XDROOT", "CLIPS001", "CONTENTS", "MP_ROOT", "M4ROOT"}
JUNK_NAMES = {".DS_Store", "Thumbs.db", "ehthumbs.db", ".Spotlight-V100", ".Trashes", ".fseventsd", ".TemporaryItems",
              "@eaDir", "#recycle", "#snapshot", ".@__thumb", "@Recycle", ".@__qini", "$RECYCLE.BIN",
              "System Volume Information", ".AppleDouble", ".AppleDB", ".AppleDesktop", ".DocumentRevisions-V100"}
QUARANTINE_DIR = "_DA_ELIMINARE"
STATE_MARK = "_riorg_state"
ORDER = {"CREA": 1, "COPIA": 2, "SPOSTA": 3, "RINOMINA": 4, "ELIMINA": 5}
CHUNK = 1024 * 1024


def now_s():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def run_id():
    return "run_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def os_name():
    s = platform.system()
    return {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(s, s.lower())


def rel_of(full, root):
    return os.path.relpath(full, root).replace(os.sep, "/")


def is_junk(name):
    return name in JUNK_NAMES or name.startswith("._")


def is_package(name):
    n = name.lower()
    return n.endswith(PACKAGE_SUFFIXES)


def fmt_bytes(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or u == "TB":
            return ("%.1f %s" % (n, u)).replace(".", ",")
        n /= 1024.0


def mtime_s(st):
    return dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M:%S")


def write_metrics(state, rec):
    rec = dict(rec)
    rec.update({"ts": now_s(), "engine": ENGINE, "os": os_name(), "python": platform.python_version()})
    os.makedirs(state, exist_ok=True)
    with open(os.path.join(state, "riorg_metrics.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def md5_file(path, partial=False):
    h = hashlib.md5()
    with open(path, "rb") as f:
        if not partial:
            while True:
                b = f.read(CHUNK)
                if not b:
                    break
                h.update(b)
        else:
            size = os.fstat(f.fileno()).st_size
            h.update(str(size).encode())
            h.update(f.read(CHUNK))
            if size > 2 * CHUNK:
                f.seek(size - CHUNK)
                h.update(f.read(CHUNK))
    return h.hexdigest().upper()


def dir_size(path):
    tot, n = 0, 0
    for r, ds, fs in os.walk(path):
        for x in fs:
            try:
                tot += os.lstat(os.path.join(r, x)).st_size
                n += 1
            except OSError:
                pass
    return tot, n


# ---------------------------------------------------------------- walk (condiviso)
def walk(target, include_protected=False, skip_names=()):
    """Genera (kind, full, st, unit) -- kind: file | unit | emptydir; conta errori."""
    errors = []
    stack = [(target, None)]
    while stack:
        d, unit = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError as e:
            errors.append("%s :: %s" % (d, e.__class__.__name__))
            continue
        if not entries and d != target:
            yield ("emptydir", d, None, unit), errors
        for e in entries:
            name = e.name
            if is_junk(name) or name in skip_names:
                continue
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    if not include_protected and (name in PROTECTED_NAMES or is_package(name)):
                        size, n = dir_size(e.path)
                        yield ("unit", e.path, (size, n), unit), errors
                        continue
                    u = unit
                    if u is None and name.upper() in CARD_ROOTS:
                        u = e.path
                    stack.append((e.path, u))
                else:
                    st = e.stat(follow_symlinks=False)
                    yield ("file", e.path, st, unit), errors
            except OSError as ex:
                errors.append("%s :: %s" % (e.path, ex.__class__.__name__))
    yield ("end", None, None, None), errors


# ---------------------------------------------------------------- env
def detect_fs(path):
    """(tipo_fs, tipo_unita) al meglio delle possibilita' del sistema."""
    osn = os_name()
    try:
        if osn == "windows":
            import ctypes
            root = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
            dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
            kinds = {2: "removable", 3: "fixed", 4: "network", 5: "cdrom", 6: "ramdisk"}
            fsbuf = ctypes.create_unicode_buffer(64)
            ctypes.windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(root), None, 0, None, None, None, fsbuf, 64)
            return (fsbuf.value or "?", kinds.get(dtype, "?"))
        if osn == "linux":
            best = ("", "?", "?")
            ap = os.path.realpath(path)
            with open("/proc/mounts") as f:
                for line in f:
                    p = line.split()
                    mp = p[1].replace("\\040", " ")
                    if (ap == mp or ap.startswith(mp.rstrip("/") + "/")) and len(mp) >= len(best[0]):
                        best = (mp, p[2], p[0])
            kind = "network" if best[1] in ("cifs", "smb3", "nfs", "nfs4", "smbfs", "9p", "virtiofs", "fuse.sshfs") else "local"
            if best[1] in ("9p", "virtiofs"):
                kind = "vm-share"
            return (best[1], kind)
        if osn == "macos":
            out = subprocess.run(["mount"], capture_output=True, text=True, timeout=10).stdout
            ap = os.path.realpath(path)
            best = ("", "?", "")
            for line in out.splitlines():
                m = re.match(r"^(.*) on (.*) \(([^,)]+)(.*)\)$", line)
                if m:
                    mp = m.group(2)
                    if (ap == mp or ap.startswith(mp.rstrip("/") + "/")) and len(mp) >= len(best[0]):
                        best = (mp, m.group(3), m.group(4))
            fs = best[1]
            kind = "network" if fs in ("smbfs", "afpfs", "nfs", "webdav") else ("local" if "local" in best[2] else "?")
            return (fs, kind)
    except Exception as e:  # mai bloccare env
        return ("?", "? (%s)" % e.__class__.__name__)
    return ("?", "?")


def cmd_env(a):
    tools = {t: bool(shutil.which(t)) for t in ("powershell", "pwsh", "rsync", "ditto", "exiftool", "ffprobe",
                                                 "mediainfo", "md5sum", "md5", "shasum", "git", "osascript")}
    info = {"engine": ENGINE, "os": os_name(), "platform": platform.platform(), "python": platform.python_version(),
            "machine": platform.machine(), "cwd": os.getcwd(), "tools": tools, "paths": []}
    if info["os"] == "linux" and os.path.exists("/proc/mounts"):
        info["note"] = "Linux: se i volumi risultano 9p/virtiofs, questa shell e' uno spazio di lavoro virtuale: il Cestino del sistema ospite non esiste qui."
    for p in (a.paths or []):
        r = {"path": p, "exists": os.path.exists(p)}
        if r["exists"]:
            r["readable"] = os.access(p, os.R_OK)
            r["writable"] = os.access(p, os.W_OK)
            try:
                du = shutil.disk_usage(p)
                r["free"] = fmt_bytes(du.free)
                r["total"] = fmt_bytes(du.total)
            except OSError:
                pass
            r["fs"], r["kind"] = detect_fs(p)
            try:
                r["first_entries"] = len(os.listdir(p)[:50])
            except OSError as e:
                r["first_entries"] = "ERRORE " + e.__class__.__name__
            if r["fs"].lower() == "ntfs" and info["os"] == "macos":
                r["warning"] = "NTFS su macOS: sola lettura. Non usarlo come destinazione."
            if r["kind"] in ("network", "removable"):
                r["cestino"] = "assente o non garantito su questa unita': ELIMINA solo in quarantena"
        info["paths"].append(r)
    print(json.dumps(info, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- scan
def load_cache(state):
    p = os.path.join(state, "riorg_cache.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            print("Cache illeggibile: ricalcolo.")
    return {"schema": 1, "files": {}, "units": {}}


def save_cache(state, cache):
    p = os.path.join(state, "riorg_cache.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, p)


def cmd_scan(a):
    t0 = time.time()
    target = os.path.abspath(a.target)
    if not os.path.isdir(target):
        sys.exit("Target non trovato: %s" % target)
    state = os.path.abspath(a.state)
    os.makedirs(state, exist_ok=True)
    prev = {} if a.no_cache else load_cache(state).get("files", {})
    skip = {QUARANTINE_DIR, os.path.basename(state)} if state.startswith(target) else {QUARANTINE_DIR}
    files, units, empties, errors = {}, {}, 0, []
    rows = []
    hits = 0
    bytes_tot = 0
    for (kind, full, st, unit), errs in walk(target, a.include_protected, skip):
        errors = errs
        if kind == "end":
            break
        if kind == "emptydir":
            empties += 1
            continue
        rel = rel_of(full, target)
        if kind == "unit":
            size, n = st
            units[rel] = {"size": size, "files": n}
            rows.append([rel, size, "", "", "unit", ""])
            bytes_tot += size
            continue
        m = mtime_s(st)
        ext = os.path.splitext(full)[1].lower()
        u = rel_of(unit, target) if unit else ""
        rows.append([rel, st.st_size, m, ext, "file", u])
        bytes_tot += st.st_size
        h = prev.get(rel)
        if h and h.get("size") == st.st_size and h.get("mtime") == m:
            files[rel] = h
            hits += 1
        else:
            files[rel] = {"size": st.st_size, "mtime": m, "md5": None, "classe": None, "conf": None}
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    csvp = os.path.join(state, "scan_%s.csv" % stamp)
    with open(csvp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["path", "size", "mtime", "ext", "kind", "unit"])
        w.writerows(rows)
    save_cache(state, {"schema": 1, "engine": ENGINE, "scan_ts": now_s(), "target": target, "files": files, "units": units})
    dur = time.time() - t0
    bysize = {}
    for r, v in files.items():
        if v["size"] > 0:
            bysize.setdefault(v["size"], 0)
            bysize[v["size"]] += 1
    cand = sum(c for c in bysize.values() if c > 1)
    exts = {}
    for r in rows:
        if r[4] == "file":
            exts[r[3] or "(nessuna)"] = exts.get(r[3] or "(nessuna)", 0) + 1
    print("=== SCAN %s ===  [%s · %s]" % (target, ENGINE, os_name()))
    print("File: %d · Dimensione: %s · Cartelle vuote: %d · Candidati doppioni per dimensione: %d" % (len(files), fmt_bytes(bytes_tot), empties, cand))
    if units:
        print("Zone protette / pacchetti (unita' intere, interni esclusi): %d" % len(units))
        for k in list(units)[:5]:
            print("  [unita'] %s  (%d file, %s)" % (k, units[k]["files"], fmt_bytes(units[k]["size"])))
    cards = sorted({r[5] for r in rows if r[5]})
    if cards:
        print("Strutture di scheda camera (da tenere intere): %d  es. %s" % (len(cards), ", ".join(cards[:3])))
    print("Per estensione (top 15):")
    for e_, n in sorted(exts.items(), key=lambda kv: -kv[1])[:15]:
        print("  %-10s %d" % (e_, n))
    print("AUTOCONTROLLO: voci lette %d (file %d + unita' %d) · cache riusata %d · errori di lettura %d · %.1f s · %.0f file/s"
          % (len(rows), len(files), len(units), hits, len(errors), dur, len(rows) / dur if dur else 0))
    if errors:
        print("  ⚠ DATI INCOMPLETI: %d cartelle/file illeggibili (permessi?). Prime: %s" % (len(errors), " | ".join(errors[:3])))
    if not rows:
        print("  ⚠ ZERO voci: prima di crederci verifica permessi e percorso con un file che sai esistere.")
    print("CSV: %s" % csvp)
    write_metrics(state, {"cmd": "scan", "target": target, "files": len(files), "units": len(units), "bytes": bytes_tot,
                          "empty_dirs": empties, "errors": len(errors), "cache_hits": hits, "duration_s": round(dur, 3),
                          "files_per_s": round(len(rows) / dur, 1) if dur else None, "size_candidates": cand})


# ---------------------------------------------------------------- dedup
def _dedup_core(items, partial):
    """items: {chiave: (percorso_completo, voce_cache)}. Dimensione -> impronta rapida (opz.) -> MD5 pieno."""
    bysize = {}
    for k, (full, v) in items.items():
        if v["size"] > 0:
            bysize.setdefault(v["size"], []).append(k)
    groups = [g for g in bysize.values() if len(g) > 1]
    st = {"candidates": sum(len(g) for g in groups), "partial": 0, "full": 0, "bytes": 0, "t_hash": 0.0}
    dups = []
    for g in groups:
        pool = [g]
        if partial and items[g[0]][1]["size"] > 2 * CHUNK:
            fp = {}
            for k in g:
                full, v = items[k]
                if not v.get("fp"):
                    th = time.time()
                    try:
                        v["fp"] = md5_file(full, partial=True)
                    except OSError:
                        v["fp"] = "ERR"
                    st["t_hash"] += time.time() - th
                    st["partial"] += 1
                    st["bytes"] += min(v["size"], 2 * CHUNK)
                if v["fp"] != "ERR":
                    fp.setdefault(v["fp"], []).append(k)
            pool = [x for x in fp.values() if len(x) > 1]
        for sub in pool:
            bym = {}
            for k in sub:
                full, v = items[k]
                if not v.get("md5"):
                    try:
                        th = time.time()
                        v["md5"] = md5_file(full)
                        st["t_hash"] += time.time() - th
                        st["full"] += 1
                        st["bytes"] += v["size"]
                    except OSError:
                        v["md5"] = "ERR"
                bym.setdefault(v["md5"], []).append(k)
            for h, x in bym.items():
                if len(x) > 1 and h != "ERR":
                    dups.append((h, items[x[0]][1]["size"], sorted(x)))
    return dups, st


def _dedup_report(state, dups, st, t0, show, target_label, csv_prefix, cmdname):
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    outp = os.path.join(state, "%s_%s.csv" % (csv_prefix, stamp))
    order = sorted(dups, key=lambda t: -t[1] * (len(t[2]) - 1))
    with open(outp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["md5", "size", "copie", "percorsi"])
        for k, sz, x in order:
            w.writerow([k, sz, len(x), " | ".join(x)])
    redundant = sum(sz * (len(x) - 1) for _, sz, x in dups)
    dur = time.time() - t0
    print("=== %s === Gruppi duplicati: %d · file coinvolti: %d · ridondanza: %s" % (cmdname.upper(), len(dups), sum(len(x) for _, _, x in dups), fmt_bytes(redundant)))
    for k, sz, x in order[:show]:
        print("MD5 %s (%d copie, %s):" % (k[:8], len(x), fmt_bytes(sz)))
        for r in x[:4]:
            print("   " + r)
    mbps = (st["bytes"] / 1048576) / st["t_hash"] if st["t_hash"] > 0 else 0
    print("AUTOCONTROLLO: candidati per dimensione %d · impronte rapide %d · MD5 pieni %d · letti %s · %.1f MB/s · %.1f s"
          % (st["candidates"], st["partial"], st["full"], fmt_bytes(st["bytes"]), mbps, dur))
    if st["candidates"] > 0 and not dups:
        print("  ⚠ Zero doppioni con %d candidati: plausibile, ma validalo con un positivo noto prima di scriverlo." % st["candidates"])
    print("CSV: %s" % outp)
    write_metrics(state, {"cmd": cmdname, "target": target_label, "candidates": st["candidates"], "partial_hashes": st["partial"],
                          "full_hashes": st["full"], "groups": len(dups), "redundant_bytes": redundant, "bytes_hashed": st["bytes"],
                          "hash_mb_s": round(mbps, 1), "duration_s": round(dur, 3)})


def cmd_dedup(a):
    t0 = time.time()
    target = os.path.abspath(a.target)
    state = os.path.abspath(a.state)
    cache = load_cache(state)
    files = cache.get("files", {})
    if not files:
        sys.exit("Cache assente o vuota: esegui prima scan.")
    items = {r: (os.path.join(target, *r.split("/")), v) for r, v in files.items()}
    dups, st = _dedup_core(items, a.partial)
    save_cache(state, cache)
    _dedup_report(state, dups, st, t0, a.show, target, "dedup", "dedup")


def cmd_dedup_multi(a):
    """Doppioni FRA piu' radici (es. due NAS + dischi), ciascuna con la sua cartella di stato gia' scansionata."""
    t0 = time.time()
    only = None
    if a.only:
        with open(a.only, encoding="utf-8-sig") as f:
            only = {os.path.normcase(os.path.abspath(x.strip())) for x in f if x.strip()}
    items, caches = {}, []
    for target, state in a.pair:
        target, state = os.path.abspath(target), os.path.abspath(state)
        c = load_cache(state)
        if not c.get("files"):
            sys.exit("Cache assente o vuota in %s: esegui prima scan su %s" % (state, target))
        caches.append((state, c))
        for r, v in c["files"].items():
            full = os.path.join(target, *r.split("/"))
            if only is not None and os.path.normcase(full) not in only:
                continue
            items[full] = (full, v)
    if only is not None:
        print("Filtro --only: %d percorsi richiesti, %d trovati nelle cache" % (len(only), len(items)))
    dups, st = _dedup_core(items, a.partial)
    for state, c in caches:
        save_cache(state, c)
    out_state = os.path.abspath(a.out_state or a.pair[0][1])
    _dedup_report(out_state, dups, st, t0, a.show, " + ".join(os.path.abspath(p[0]) for p in a.pair), "dedup_multi", "dedup-multi")


# ---------------------------------------------------------------- execute / undo
class Journal:
    def __init__(self, state, rid):
        self.path = os.path.join(state, "riorg_undo_%s.jsonl" % rid)
        with open(os.path.join(state, "riorg_undo_last.txt"), "w", encoding="utf-8") as f:
            f.write(self.path)
        self.n = 0

    def add(self, rec):
        self.n += 1
        rec = dict(rec, n=self.n, ts=now_s())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return self.n


def existing_ancestor(p):
    p = os.path.abspath(p)
    while not os.path.exists(p):
        q = os.path.dirname(p)
        if q == p:
            break
        p = q
    return p


def same_device(a_, b_):
    try:
        return os.stat(existing_ancestor(a_)).st_dev == os.stat(existing_ancestor(b_)).st_dev
    except OSError:
        return False


def qdest_for(src, qroot, rid):
    src = os.path.abspath(src)
    qroot = os.path.abspath(qroot)
    try:
        rel = os.path.relpath(src, qroot)
    except ValueError:
        rel = os.path.basename(src)
    if rel.startswith(".."):
        rel = os.path.basename(src)
    return os.path.join(qroot, QUARANTINE_DIR, rid, rel)


def plan_sizes(src):
    if os.path.isdir(src):
        return dir_size(src)[0]
    return os.path.getsize(src)


def validate(ops, qroot, rid):
    warns = []
    need = {}
    seen = {}
    for o in ops:
        t, da, a_ = o["tipo"], o.get("da"), o.get("a")
        tag = "%s seq %d" % (t, o["seq"])
        if t not in ORDER:
            warns.append("[%s] tipo non supportato da riorg.py (MERGE/FLATTEN: usa execute.ps1 su Windows o spezza in SPOSTA)" % tag)
            continue
        if t != "CREA" and (not da or not os.path.exists(da)):
            warns.append("[%s] sorgente assente: %s" % (tag, da))
            continue
        if t in ("COPIA", "SPOSTA", "RINOMINA"):
            if not a_:
                warns.append("[%s] destinazione mancante" % tag)
                continue
            if os.path.exists(a_):
                if t == "COPIA" and os.path.isfile(da) and os.path.isfile(a_) and os.path.getsize(da) == os.path.getsize(a_):
                    o["_skip"] = True
                elif not (t == "COPIA" and os.path.isdir(da) and os.path.isdir(a_)):
                    warns.append("[%s] destinazione gia' esistente: %s" % (tag, a_))
            if t in ("SPOSTA", "RINOMINA") and not same_device(da, a_):
                warns.append("[%s] volumi diversi: uno spostamento diventerebbe copia+cancellazione. Usa COPIA (e poi ELIMINA in quarantena)." % tag)
            if t == "COPIA" and not o.get("_skip"):
                dev = existing_ancestor(a_)
                need[dev] = need.get(dev, 0) + plan_sizes(da)
        if t == "ELIMINA":
            if not qroot:
                warns.append("[%s] ELIMINA richiede --quarantine-root (la quarantena sta sullo stesso volume)" % tag)
            elif not same_device(da, qroot):
                warns.append("[%s] la quarantena %s non e' sullo stesso volume di %s" % (tag, qroot, da))
            else:
                o["a"] = qdest_for(da, qroot, rid)
                if os.path.exists(o["a"]):
                    warns.append("[%s] in quarantena esiste gia': %s" % (tag, o["a"]))
        dest = o.get("a")
        if dest and t != "CREA":
            k = os.path.normcase(os.path.abspath(dest))
            if k in seen:
                warns.append("[%s] stessa destinazione di seq %d: %s (sovrascriverebbe)" % (tag, seen[k], dest))
            seen[k] = o["seq"]
    for dev, b in need.items():
        try:
            free = shutil.disk_usage(dev).free
            if b * 1.05 > free:
                warns.append("[COPIA] spazio insufficiente su %s: servono %s (+5%%), liberi %s" % (dev, fmt_bytes(b), fmt_bytes(free)))
        except OSError:
            pass
    return warns, need


def mkdirs_journaled(path, jr):
    """Crea le cartelle mancanti registrando ciascuna come CREA (undo le rimuove se vuote)."""
    missing = []
    p = os.path.abspath(path)
    while not os.path.exists(p):
        missing.append(p)
        q = os.path.dirname(p)
        if q == p:
            break
        p = q
    for d in reversed(missing):
        if jr:
            jr.add({"tipo": "CREA", "a": d, "created": True, "auto": True})
        os.mkdir(d)


def copy_file(src, dst, verify):
    part = dst + ".riorg-part"
    shutil.copy2(src, part)
    os.replace(part, dst)
    if os.path.getsize(src) != os.path.getsize(dst):
        raise IOError("dimensione diversa dopo la copia: %s" % dst)
    if verify == "md5" and md5_file(src) != md5_file(dst):
        raise IOError("MD5 diverso dopo la copia: %s" % dst)


def cmd_execute(a):
    t0 = time.time()
    state = os.path.abspath(a.state)
    os.makedirs(state, exist_ok=True)
    with open(a.ops, encoding="utf-8-sig") as f:
        ops = json.load(f)
    for i, o in enumerate(ops, 1):
        o["seq"] = i
        o["tipo"] = str(o.get("tipo", "")).upper()
    ops.sort(key=lambda o: (ORDER.get(o["tipo"], 99), o["seq"]))
    rid = run_id()
    warns, need = validate(ops, a.quarantine_root, rid)
    real = a.real
    tag = "[REALE]" if real else "[DRY]"
    print("=== EXECUTE %s · %s · %d op · %s ===" % (ENGINE, os_name(), len(ops), rid))
    for w in warns:
        print("WARN " + w)
    print("VALIDAZIONE: %d WARN." % len(warns))
    if warns:
        print("Correggi le WARN: con WARN > 0 il reale non parte.")
        write_metrics(state, {"cmd": "execute", "real": False, "ops": len(ops), "warns": len(warns), "duration_s": round(time.time() - t0, 3)})
        sys.exit(2)
    for dev, b in need.items():
        print("Copia prevista su %s: %s" % (dev, fmt_bytes(b)))
    if not real:
        for o in ops:
            print("%s %s: %s -> %s%s" % (tag, o["tipo"], o.get("da") or "", o.get("a") or "", "  (gia' presente, salto)" if o.get("_skip") else ""))
        print("DRY-RUN: nessuna scrittura. Per il reale: --real (dopo conferma esplicita; ELIMINA vuole «PROCEDI»).")
        write_metrics(state, {"cmd": "execute", "real": False, "ops": len(ops), "warns": 0, "duration_s": round(time.time() - t0, 3)})
        return
    jr = Journal(state, rid)
    done = {k: 0 for k in ORDER}
    copied_bytes = skipped = 0
    try:
        for o in ops:
            t, da, a_ = o["tipo"], o.get("da"), o.get("a")
            print("%s %s: %s -> %s" % (tag, t, da or "", a_ or ""))
            if t == "CREA":
                existed = os.path.isdir(a_)
                mkdirs_journaled(os.path.dirname(os.path.abspath(a_)), jr)
                jr.add({"tipo": "CREA", "a": a_, "created": not existed, "seq": o["seq"]})
                if not existed:
                    os.mkdir(a_)
            elif t == "COPIA":
                if o.get("_skip"):
                    skipped += 1
                    jr.add({"tipo": "NOTA", "msg": "gia' presente, non ricopiato", "da": da, "a": a_})
                    continue
                n = jr.add({"tipo": "COPIA_INIZIO", "da": da, "a": a_, "seq": o["seq"]})
                if os.path.isdir(da):
                    for r, ds, fs in os.walk(da):
                        ds[:] = [x for x in ds if not os.path.islink(os.path.join(r, x))]
                        tr = os.path.join(a_, os.path.relpath(r, da))
                        mkdirs_journaled(tr, jr)
                        for x in fs:
                            s, d = os.path.join(r, x), os.path.join(tr, x)
                            if os.path.islink(s):
                                continue
                            if os.path.exists(d) and os.path.getsize(d) == os.path.getsize(s):
                                skipped += 1
                                continue
                            jr.add({"tipo": "COPIA", "da": s, "a": d, "size": os.path.getsize(s), "parent": n})
                            if os.path.exists(d):
                                raise IOError("destinazione occupata con contenuto diverso: %s" % d)
                            copy_file(s, d, a.verify)
                            copied_bytes += os.path.getsize(d)
                else:
                    mkdirs_journaled(os.path.dirname(os.path.abspath(a_)), jr)
                    if os.path.exists(a_):
                        raise IOError("destinazione occupata: %s" % a_)
                    jr.add({"tipo": "COPIA", "da": da, "a": a_, "size": os.path.getsize(da), "parent": n})
                    copy_file(da, a_, a.verify)
                    copied_bytes += os.path.getsize(a_)
            elif t in ("SPOSTA", "RINOMINA", "ELIMINA"):
                mkdirs_journaled(os.path.dirname(os.path.abspath(a_)), jr)
                if os.path.exists(a_):
                    raise IOError("destinazione occupata al momento dell'azione: %s" % a_)
                jr.add({"tipo": t, "da": da, "a": a_, "seq": o["seq"]})
                os.rename(da, a_)
            done[t] += 1
    except Exception as e:
        print("ERRORE: %s -- esecuzione fermata. Journal: %s (undo disponibile)" % (e, jr.path))
        write_metrics(state, {"cmd": "execute", "real": True, "run": rid, "error": str(e), "done": done,
                              "duration_s": round(time.time() - t0, 3)})
        sys.exit(1)
    dur = time.time() - t0
    mbps = (copied_bytes / 1048576) / dur if dur > 0 else 0
    print("FATTO: %s · copiati %s (%.1f MB/s) · gia' presenti %d · %.1f s" % (", ".join("%s %d" % kv for kv in done.items() if kv[1]), fmt_bytes(copied_bytes), mbps, skipped, dur))
    if done["ELIMINA"]:
        print("Quarantena: %s  -- niente e' cancellato: svuotala tu quando hai riletto." % os.path.join(os.path.abspath(a.quarantine_root), QUARANTINE_DIR, rid))
    print("Journal: %s" % jr.path)
    write_metrics(state, {"cmd": "execute", "real": True, "run": rid, "done": done, "copied_bytes": copied_bytes,
                          "copy_mb_s": round(mbps, 1), "skipped": skipped, "journal_entries": jr.n, "duration_s": round(dur, 3)})


def cmd_undo(a):
    t0 = time.time()
    state = os.path.abspath(a.state)
    jp = a.journal
    if not jp:
        with open(os.path.join(state, "riorg_undo_last.txt"), encoding="utf-8") as f:
            jp = f.read().strip()
    elif not os.path.isabs(jp):
        jp = os.path.join(state, jp)
    with open(jp, encoding="utf-8") as f:
        recs = [json.loads(x) for x in f if x.strip()]
    tag = "[REALE]" if a.real else "[DRY]"
    print("=== UNDO %s · %d voci · LIFO ===" % (os.path.basename(jp), len(recs)))
    ok = skip = 0
    for r in reversed(recs):
        t = r["tipo"]
        if t in ("NOTA", "COPIA_INIZIO"):
            continue
        if t == "CREA":
            if not r.get("created"):
                continue
            print("%s CREA -> rimuovi se vuota: %s" % (tag, r["a"]))
            if a.real:
                try:
                    os.rmdir(r["a"])
                    ok += 1
                except OSError:
                    print("  salto: non vuota o assente (mai rimozione ricorsiva)")
                    skip += 1
        elif t == "COPIA":
            print("%s COPIA -> togli la copia: %s" % (tag, r["a"]))
            if a.real:
                if os.path.isfile(r["a"]) and os.path.getsize(r["a"]) == r.get("size"):
                    os.remove(r["a"])
                    ok += 1
                else:
                    print("  salto: copia assente o cambiata dopo la run")
                    skip += 1
        elif t in ("SPOSTA", "RINOMINA", "ELIMINA"):
            print("%s %s -> riporta: %s <- %s" % (tag, t, r["da"], r["a"]))
            if a.real:
                if not os.path.exists(r["a"]):
                    print("  salto: %s non esiste piu'" % r["a"])
                    skip += 1
                elif os.path.exists(r["da"]):
                    print("  salto: %s occupato (collisione)" % r["da"])
                    skip += 1
                else:
                    os.makedirs(os.path.dirname(r["da"]), exist_ok=True)
                    os.rename(r["a"], r["da"])
                    ok += 1
    if a.real:
        print("UNDO completato: %d ok, %d saltate." % (ok, skip))
    else:
        print("DRY-RUN undo: nessuna modifica. Per il reale: --real.")
    write_metrics(state, {"cmd": "undo", "real": a.real, "ok": ok, "skipped": skip, "duration_s": round(time.time() - t0, 3)})


# ---------------------------------------------------------------- albero (porta di albero.ps1, prefisso ax)
FOLD = "<svg viewBox='0 0 24 24' width='15' height='15'><path fill='#e0a92e' d='M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8z'/></svg>"
FILEI = "<svg viewBox='0 0 24 24' width='14' height='14'><path fill='#8a8f98' d='M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z'/><path fill='#5b6069' d='M14 2l6 6h-6z'/></svg>"
ALB_CSS = """body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px/1.55 'Segoe UI',system-ui,sans-serif}
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
.expr{display:flex;gap:8px;margin-top:6px;align-items:center}"""
ALB_JS = """
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
  var out='# Risposte verifica albero - '+new Date().toLocaleString('it-IT')+'\\n\\n';
  if(!keys.length){ out+='(nessun commento inserito)\\n'; } else { keys.sort().forEach(function(p){ var c=o[p]; out+='- ['+c.tag+'] '+p+(c.text?(' -- '+c.text):'')+'\\n'; }); }
  ta.value=out; w.style.display='block'; document.getElementById('expInfo').textContent=keys.length+' righe commentate'; ta.focus(); ta.select();
}
function axcopyExp(){ var ta=document.getElementById('exp'); ta.select(); try{document.execCommand('copy');}catch(e){} }
function axdlExp(){ var ta=document.getElementById('exp'); var bl=new Blob([ta.value],{type:'text/markdown'}); var a=document.createElement('a'); a.href=URL.createObjectURL(bl); a.download='risposte_albero.md'; a.click(); }
(function(){ var o=getC(); document.querySelectorAll('.r').forEach(function(r){ var p=r.getAttribute('data-path'); if(o[p]) markRow(r,o[p].tag); }); })();
</script>
"""


def albero_check_text(t):
    on = sorted(set(re.findall(r"onclick=['\"]?([A-Za-z_]\w*)\(", t)))
    fn = set(re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", t))
    bad_all = len(re.findall(r"(function\s+all\(|onclick=['\"]?all\()", t))
    orphans = [x for x in on if x not in fn]
    noax = [x for x in on if not x.startswith("ax")]
    return bad_all, orphans, noax, on


def cmd_albero(a):
    if a.check:
        with open(a.check, encoding="utf-8-sig") as f:
            t = f.read()
        bad, orph, noax, on = albero_check_text(t)
        ok = not bad and not orph and not noax
        print("PRE-FLIGHT albero: all( residui %d · orfane %s · senza prefisso ax %s · handler %s -> %s"
              % (bad, orph or "[]", noax or "[]", ",".join(on), "OK" if ok else "FALLITO"))
        sys.exit(0 if ok else 3)
    target = os.path.abspath(a.target)
    title = a.title or os.path.basename(target.rstrip("/\\"))
    rows, cnt = [], {"d": 0, "f": 0}

    def ls(d):
        try:
            it = [e for e in os.scandir(d) if a.show_junk or not is_junk(e.name)]
        except OSError:
            return []
        return sorted(it, key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))

    def emit(d, depth):
        for e in ls(d):
            pad = 8 + depth * 20
            nm = html.escape(e.name, quote=False)
            pa = html.escape(e.path, quote=True).replace("'", "&#39;")
            if e.is_dir(follow_symlinks=False):
                cnt["d"] += 1
                n = len(ls(e.path))
                rows.append("<div class='node'><div class='r d' data-path='%s' style='padding-left:%dpx'><span class='cv' onclick='axtg(this)'>&#9662;</span>%s<span class='nm'>%s</span><span class='ct'>%d</span><button class='cm' onclick='axnote(this)' title='Commenta'>&#128172;</button></div><div class='children'>" % (pa, pad, FOLD, nm, n))
                emit(e.path, depth + 1)
                rows.append("</div></div>")
            else:
                cnt["f"] += 1
                rows.append("<div class='r f' data-path='%s' style='padding-left:%dpx'><span class='cv'>&nbsp;</span>%s<span class='nm'>%s</span><button class='cm' onclick='axnote(this)' title='Commenta'>&#128172;</button></div>" % (pa, pad, FILEI, nm))

    emit(target, 0)
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    t_ = html.escape(title)
    head = ("<!DOCTYPE html>\n<!-- Header Cowork v1.0 | albero debrief (%s) | %s -->\n<html lang='it'><head><meta charset='UTF-8'><title>%s - albero verifica</title><style>\n%s\n</style></head><body>\n"
            "<div class='top'><h1>&#128193; %s &mdash; verifica</h1>\n<span class='s'>%d cartelle &middot; %d file &middot; %s</span><span style='flex:1'></span>\n"
            "<button class='btn' onclick='axSetAll(false)'>Espandi</button><button class='btn' onclick='axSetAll(true)'>Collassa</button>\n"
            "<button class='btn exp' onclick='axexportC()'>Esporta risposte</button></div>\n<div class='tree'>\n") % (ENGINE, ts, t_, ALB_CSS, t_, cnt["d"], cnt["f"], ts)
    doc = head + "\n".join(rows) + "\n</div>" + ALB_JS + "</body></html>"
    bad, orph, noax, _ = albero_check_text(doc)
    if bad or orph or noax:
        sys.exit("PRE-FLIGHT FALLITO sul generatore: all(=%d orfane=%s senza-ax=%s. Albero NON scritto." % (bad, orph, noax))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("Albero generato: %s  (%d cartelle, %d file) · pre-flight OK" % (a.out, cnt["d"], cnt["f"]))


# ---------------------------------------------------------------- bench
def build_fixture(root, seed, scale):
    rnd = random.Random(seed)
    mult = {"small": 1, "medium": 5}[scale]
    exp = {"files": 0, "units": 0, "dup_groups": [], "junk": 0, "cards": 0}

    def put(rel, data):
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        return rel

    def blob(n):
        return bytes(rnd.getrandbits(8) for _ in range(n)) if n < 4096 else rnd.randbytes(n) if hasattr(rnd, "randbytes") else os.urandom(n)

    names = ["L'evento dell'anno", "Sant'Anna", "caffè e ù", "Città [bozza] (2)", "file con  spazi", "Ñandú_ß", "BOZZA FINALE v2"]
    clients = ["ClienteA", "ClienteB", "ClienteC"]
    exts = [".mp4", ".mov", ".jpg", ".pdf", ".wav", ".prproj", ".txt"]
    for c in clients:
        for y in ("2024", "2025"):
            for i in range(40 * mult):
                ext = rnd.choice(exts)
                size = rnd.choice([0, 12, 700, 5000, 60000, 300000])
                nm = rnd.choice(names) + "_%03d%s" % (i, ext)
                put("Lavori/%s/%s/%s" % (c, y, nm), blob(size))
                exp["files"] += 1
    # doppioni veri (contenuto identico) -- grandi e piccoli, incluso uno > 2 MB per l'impronta rapida
    for g in range(6 * mult):
        size = 2 * CHUNK + 777 if g == 0 else rnd.choice([1500, 40000, 250000])
        data = blob(size)
        paths = []
        for k in range(rnd.choice([2, 3])):
            paths.append(put("Doppi/copia%d/g%02d/%s_%d.bin" % (k, g, names[g % len(names)].replace("/", "-"), g), data))
            exp["files"] += 1
        exp["dup_groups"].append(sorted(paths))
    # stessa dimensione, contenuto diverso (falsi candidati)
    for g in range(4):
        for k in range(2):
            put("Quasi/q%d_%d.bin" % (g, k), blob(33333))
            exp["files"] += 1
    # stessa testa e coda, centro diverso (> 2 MB): l'impronta rapida li unisce, l'MD5 pieno li separa
    base = bytearray(blob(3 * CHUNK))
    put("Quasi/trappola_a.bin", bytes(base))
    base[CHUNK + 5] ^= 0xFF
    put("Quasi/trappola_b.bin", bytes(base))
    exp["files"] += 2
    # zone protette e pacchetti
    for i in range(30):
        put("progetto_web/.git/objects/%02d/obj%03d" % (i % 7, i), blob(200))
    for i in range(20):
        put("progetto_web/node_modules/pkg%d/index.js" % i, blob(300))
    put("progetto_web/index.html", blob(900))
    exp["files"] += 1
    for i in range(15):
        put("Montaggi/Evento Natale.fcpbundle/Original Media/clip%02d.mov" % i, blob(8000))
    exp["units"] += 3  # .git, node_modules, .fcpbundle
    for i in range(12):
        put("Schede/SD01/DCIM/100CANON/IMG_%04d.JPG" % i, blob(5000))
        exp["files"] += 1
    exp["cards"] = 1
    # spazzatura di sistema: deve sparire dall'inventario
    for j in (".DS_Store", "Lavori/._clip.mov", "Lavori/Thumbs.db", "@eaDir/x", "#recycle/y"):
        put(j, blob(100))
        exp["junk"] += 1
    os.makedirs(os.path.join(root, "Vuota", "Anche_vuota"), exist_ok=True)
    return exp


def snapshot(root, skip):
    out = {}
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if os.path.join(r, d) not in skip]
        for x in fs:
            p = os.path.join(r, x)
            out[rel_of(p, root)] = md5_file(p)
        if not fs and not ds:
            out[rel_of(r, root) + "/"] = "DIR"
    return out


def cmd_bench(a):
    work = os.path.abspath(a.work)
    if os.path.exists(work) and os.listdir(work):
        sys.exit("La cartella di bench deve essere nuova o vuota: %s" % work)
    root = os.path.join(work, "fixture")
    state = os.path.join(work, STATE_MARK)
    os.makedirs(root, exist_ok=True)
    res = {"engine": ENGINE, "os": os_name(), "platform": platform.platform(), "python": platform.python_version(),
           "scale": a.scale, "seed": a.seed, "checks": {}, "timings_s": {}, "rates": {}}
    t = time.time()
    exp = build_fixture(root, a.seed, a.scale)
    res["timings_s"]["build"] = round(time.time() - t, 3)
    before = snapshot(root, set())

    class NS(object):
        pass

    def ns(**kw):
        o = NS()
        o.__dict__.update(kw)
        return o

    def last_metric(cmd):
        with open(os.path.join(state, "riorg_metrics.jsonl"), encoding="utf-8") as f:
            ms = [json.loads(x) for x in f if x.strip()]
        return [m for m in ms if m["cmd"] == cmd][-1]

    import io, contextlib
    def quiet(fn, arg):
        buf = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(buf):
            try:
                fn(arg)
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
        return code, buf.getvalue()

    # 1 scan
    code, out = quiet(cmd_scan, ns(target=root, state=state, no_cache=True, include_protected=False))
    m = last_metric("scan")
    res["timings_s"]["scan"] = m["duration_s"]
    res["rates"]["scan_files_per_s"] = m["files_per_s"]
    res["checks"]["scan_conta_file"] = (m["files"] == exp["files"], "%d letti / %d attesi" % (m["files"], exp["files"]))
    res["checks"]["scan_unita_protette"] = (m["units"] == exp["units"], "%d / %d" % (m["units"], exp["units"]))
    sc = sorted(x for x in os.listdir(state) if x.startswith("scan_"))[-1]
    with open(os.path.join(state, sc), encoding="utf-8-sig") as f:
        paths = [r["path"] for r in csv.DictReader(f)]
    leaked = [x for x in paths if any(is_junk(seg) for seg in x.split("/"))]
    res["checks"]["scan_spazzatura_esclusa"] = (not leaked, "%d file di sistema creati, %d finiti nell'inventario" % (exp["junk"], len(leaked)))
    res["checks"]["scan_zero_errori"] = (m["errors"] == 0, "%d errori" % m["errors"])
    # 2 dedup (impronta rapida attiva)
    code, out = quiet(cmd_dedup, ns(target=root, state=state, partial=True, show=0))
    m = last_metric("dedup")
    res["timings_s"]["dedup"] = m["duration_s"]
    res["rates"]["hash_mb_s"] = m["hash_mb_s"]
    found = []
    dp = sorted(x for x in os.listdir(state) if x.startswith("dedup_"))[-1]
    with open(os.path.join(state, dp), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            found.append(sorted(r["percorsi"].split(" | ")))
    ok = sorted(found) == sorted(exp["dup_groups"])
    res["checks"]["dedup_gruppi_esatti"] = (ok, "%d trovati / %d attesi (trappole di dimensione e impronta escluse: %s)"
                                              % (len(found), len(exp["dup_groups"]), "si" if ok else "NO"))
    # 3 piano: CREA, COPIA (file + pacchetto), SPOSTA, RINOMINA (apostrofi), ELIMINA -> quarantena
    L = lambda *p: os.path.join(root, *p)
    lavori = sorted(os.listdir(L("Lavori", "ClienteC", "2025")))
    ops = [{"tipo": "CREA", "a": L("_UNICA")}, {"tipo": "CREA", "a": L("_UNICA", "2025")}]
    for x in lavori[:20]:
        ops.append({"tipo": "COPIA", "da": L("Lavori", "ClienteC", "2025", x), "a": L("_UNICA", "2025", x)})
    ops.append({"tipo": "COPIA", "da": L("Montaggi", "Evento Natale.fcpbundle"), "a": L("_UNICA", "Evento Natale.fcpbundle")})
    ops.append({"tipo": "COPIA", "da": L("Schede", "SD01"), "a": L("_UNICA", "Schede", "SD01")})
    b24 = sorted(os.listdir(L("Lavori", "ClienteA", "2024")))
    for x in b24[:10]:
        ops.append({"tipo": "SPOSTA", "da": L("Lavori", "ClienteA", "2024", x), "a": L("Lavori", "ClienteB", "2024", "spostato_" + x)})
    for x in b24[10:15]:
        ops.append({"tipo": "RINOMINA", "da": L("Lavori", "ClienteA", "2024", x), "a": L("Lavori", "ClienteA", "2024", "2024-01-01_rinominato dell'" + x)})
    for x in b24[15:25]:
        ops.append({"tipo": "ELIMINA", "da": L("Lavori", "ClienteA", "2024", x)})
    opsf = os.path.join(state, "bench_ops.json")
    with open(opsf, "w", encoding="utf-8") as f:
        json.dump(ops, f, ensure_ascii=False)
    # 2b doppioni fra radici diverse (come due NAS): Doppi/copia0 e Doppi/copia1 scansionate a parte
    ra, rb = L("Doppi", "copia0"), L("Doppi", "copia1")
    sa, sb = os.path.join(work, "_st_a"), os.path.join(work, "_st_b")
    quiet(cmd_scan, ns(target=ra, state=sa, no_cache=True, include_protected=False))
    quiet(cmd_scan, ns(target=rb, state=sb, no_cache=True, include_protected=False))
    only = os.path.join(work, "_only.txt")
    with open(only, "w", encoding="utf-8") as f:
        for r_, _, fs in os.walk(ra):
            for x in fs:
                f.write(os.path.join(r_, x) + "\n")
        for r_, _, fs in os.walk(rb):
            for x in fs:
                f.write(os.path.join(r_, x) + "\n")
    code, out = quiet(cmd_dedup_multi, ns(pair=[[ra, sa], [rb, sb]], only=only, partial=True, show=0, out_state=None))
    exp_ab = [g for g in exp["dup_groups"] if any("/copia0/" in p for p in g) and any("/copia1/" in p for p in g)]
    got = int(re.search(r"Gruppi duplicati: (\d+)", out).group(1)) if "Gruppi duplicati" in out else -1
    res["checks"]["dedup_fra_radici"] = (got == len(exp_ab), "%d gruppi fra le due radici / %d attesi" % (got, len(exp_ab)))
    # 3a piano volutamente sbagliato: la validazione deve fermarlo senza scrivere nulla
    x0, x1 = L("Lavori", "ClienteB", "2025", sorted(os.listdir(L("Lavori", "ClienteB", "2025")))[0]), L("Lavori", "ClienteB", "2025", sorted(os.listdir(L("Lavori", "ClienteB", "2025")))[1])
    bad = [{"tipo": "SPOSTA", "da": x0, "a": x1},                       # destinazione esistente
           {"tipo": "RINOMINA", "da": L("non-esiste.txt"), "a": L("x.txt")},  # sorgente assente
           {"tipo": "COPIA", "da": x0, "a": L("_Z", "a.bin")}, {"tipo": "COPIA", "da": x1, "a": L("_Z", "a.bin")},  # stessa destinazione
           {"tipo": "MERGE", "da": L("Doppi"), "a": L("Quasi")},          # non supportato qui
           {"tipo": "ELIMINA", "da": x0}]                                  # senza quarantena
    badf = os.path.join(state, "bench_ops_errati.json")
    with open(badf, "w", encoding="utf-8") as f:
        json.dump(bad, f, ensure_ascii=False)
    code, out = quiet(cmd_execute, ns(ops=badf, state=state, real=True, quarantine_root=None, verify="size"))
    nwarn = len([l for l in out.splitlines() if l.startswith("WARN ")])
    res["checks"]["validazione_ferma_i_piani_sbagliati"] = (code == 2 and nwarn >= 5 and snapshot(root, set()) == before,
                                                           "%d WARN su 5 op sbagliate (di 6), reale rifiutato, nessuna scrittura" % nwarn)
    code, out = quiet(cmd_execute, ns(ops=opsf, state=state, real=False, quarantine_root=root, verify="size"))
    res["checks"]["dryrun_zero_warn"] = (code == 0 and "VALIDAZIONE: 0 WARN" in out, "exit %s" % code)
    res["checks"]["dryrun_nessuna_scrittura"] = (snapshot(root, {L(QUARANTINE_DIR)}) == before, "albero invariato dopo il dry-run")
    code, out = quiet(cmd_execute, ns(ops=opsf, state=state, real=True, quarantine_root=root, verify="md5"))
    m = last_metric("execute")
    res["timings_s"]["execute"] = m["duration_s"]
    res["rates"]["copy_mb_s"] = m.get("copy_mb_s")
    after = snapshot(root, set())
    copies_ok = all(after.get(rel_of(o["a"], root)) == before.get(rel_of(o["da"], root)) for o in ops if o["tipo"] == "COPIA" and os.path.isfile(o["da"]))
    unit_ok = all(after.get("_UNICA/Evento Natale.fcpbundle/Original Media/clip%02d.mov" % i) == before.get("Montaggi/Evento Natale.fcpbundle/Original Media/clip%02d.mov" % i) for i in range(15))
    src_ok = all(after.get(k) == v for k, v in before.items() if k.startswith(("Lavori/ClienteC", "Montaggi/", "Schede/")))
    q = [k for k in after if k.startswith(QUARANTINE_DIR + "/")]
    res["checks"]["reale_esito"] = (code == 0, "exit %s" % code)
    res["checks"]["copie_identiche_md5"] = (copies_ok and unit_ok, "file + pacchetto .fcpbundle")
    res["checks"]["sorgenti_delle_copie_intatte"] = (src_ok, "originali invariati")
    res["checks"]["elimina_in_quarantena"] = (len(q) == 10, "%d file in %s/ (attesi 10), nessuno cancellato" % (len(q), QUARANTINE_DIR))
    # 4 resume: rilancio della sola COPIA -> tutto gia' presente, nessuna scrittura
    ops2 = [o for o in ops if o["tipo"] == "COPIA"]
    with open(opsf, "w", encoding="utf-8") as f:
        json.dump(ops2, f, ensure_ascii=False)
    code, out = quiet(cmd_execute, ns(ops=opsf, state=state, real=True, quarantine_root=root, verify="size"))
    m2 = last_metric("execute")
    res["checks"]["ripresa_senza_ricopiare"] = (code == 0 and m2.get("copied_bytes", 1) == 0, "copiati %s alla seconda passata" % m2.get("copied_bytes"))
    # 5 undo di entrambe le run (LIFO, prima la seconda)
    js = sorted(x for x in os.listdir(state) if x.startswith("riorg_undo_run_"))
    t = time.time()
    for j in reversed(js):
        quiet(cmd_undo, ns(state=state, journal=j, real=True))
    res["timings_s"]["undo"] = round(time.time() - t, 3)
    restored = snapshot(root, set())
    diff = sorted(set(restored.items()) ^ set(before.items()))
    res["checks"]["undo_ripristino_esatto"] = (not diff, "%d voci confrontate (file, contenuti MD5, cartelle vuote)%s" % (len(before), "" if not diff else " · DIFFERENZE: %s" % [d[0] for d in diff[:5]]))
    res["checks"]["undo_nessun_residuo"] = (not os.path.exists(L(QUARANTINE_DIR)) and not os.path.exists(L("_UNICA")), "quarantena e cartelle create rimosse perche' tornate vuote")
    # 6 albero + pre-flight
    outh = os.path.join(state, "bench_albero.html")
    code, out = quiet(cmd_albero, ns(check=None, target=root, out=outh, title="bench", show_junk=False))
    code2, out2 = quiet(cmd_albero, ns(check=outh))
    res["checks"]["albero_preflight_ax"] = (code == 0 and code2 == 0, out2.strip()[:120])
    # 7 confronto opzionale con v1.2.2 (PowerShell) sulla stessa cartella
    if a.compare_ps:
        res["powershell_confronto"] = dict(bench_ps(a.compare_ps, root, os.path.join(work, "_state_ps"), exp), script=os.path.abspath(a.compare_ps))
    passed = sum(1 for v in res["checks"].values() if v[0])
    res["esito"] = "%d/%d controlli superati" % (passed, len(res["checks"]))
    res["fixture"] = {"file_attesi": exp["files"], "gruppi_doppioni": len(exp["dup_groups"]), "unita": exp["units"], "spazzatura": exp["junk"]}
    outj = os.path.join(work, "bench_%s_%s.json" % (os_name(), dt.datetime.now().strftime("%Y%m%d_%H%M%S")))
    with open(outj, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("=== BENCH %s · %s · %s · scala %s ===" % (ENGINE, os_name(), platform.platform(), a.scale))
    for k, (ok, d) in res["checks"].items():
        print("  %-30s %s  %s" % (k, "PASS" if ok else "FAIL", d))
    print("  tempi (s): " + " · ".join("%s %s" % kv for kv in res["timings_s"].items()))
    print("  ritmi: scan %s file/s · hash %s MB/s · copia %s MB/s" % (res["rates"].get("scan_files_per_s"), res["rates"].get("hash_mb_s"), res["rates"].get("copy_mb_s")))
    if a.compare_ps:
        print("  PowerShell (%s): %s" % (a.compare_ps, json.dumps({k: v for k, v in res["powershell_confronto"].items() if k != "script"}, ensure_ascii=False)))
    print("ESITO: %s · report: %s" % (res["esito"], outj))
    sys.exit(0 if passed == len(res["checks"]) else 4)


def bench_ps(psdir, root, st, exp):
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return {"nota": "PowerShell assente: confronto non eseguito"}
    os.makedirs(st, exist_ok=True)
    out = {}
    for name, extra in (("scan", []), ("dedup", [])):
        t = time.time()
        p = subprocess.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(psdir, name + ".ps1"),
                            "-Target", root, "-StateDir", st] + extra, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out[name + "_s"] = round(time.time() - t, 3)
        txt = p.stdout
        if name == "scan":
            m = re.search(r"File totali:\s*(\d+)", txt)
            out["scan_file"] = int(m.group(1)) if m else None
            out["scan_attesi_v13"] = exp["files"]
            out["nota_scan"] = "scan.ps1 conta anche spazzatura di sistema e interni dei pacchetti (.fcpbundle): differenza attesa"
        else:
            m = re.search(r"Gruppi duplicati:\s*(\d+)", txt)
            out["dedup_gruppi"] = int(m.group(1)) if m else None
            out["dedup_attesi"] = len(exp["dup_groups"])
        if p.returncode != 0:
            out[name + "_errore"] = (p.stderr or "")[:300]
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd")
    p = sp.add_parser("env"); p.add_argument("paths", nargs="*")
    p = sp.add_parser("scan"); p.add_argument("--target", required=True); p.add_argument("--state", required=True)
    p.add_argument("--no-cache", action="store_true"); p.add_argument("--include-protected", action="store_true")
    p = sp.add_parser("dedup"); p.add_argument("--target", required=True); p.add_argument("--state", required=True)
    p.add_argument("--partial", action="store_true", help="impronta rapida (1 MB testa+coda) prima dell'MD5 pieno")
    p.add_argument("--show", type=int, default=15)
    p = sp.add_parser("dedup-multi", help="doppioni fra piu' radici gia' scansionate")
    p.add_argument("--pair", nargs=2, action="append", required=True, metavar=("TARGET", "STATE"))
    p.add_argument("--only", default=None, help="file di testo: un percorso assoluto per riga (es. i candidati della caccia)")
    p.add_argument("--partial", action="store_true"); p.add_argument("--show", type=int, default=15)
    p.add_argument("--out-state", default=None, help="dove scrivere CSV e metriche (default: stato della prima coppia)")
    p = sp.add_parser("execute"); p.add_argument("--ops", required=True); p.add_argument("--state", required=True)
    p.add_argument("--real", action="store_true"); p.add_argument("--quarantine-root", default=None)
    p.add_argument("--verify", choices=["size", "md5"], default="size")
    p = sp.add_parser("undo"); p.add_argument("--state", required=True); p.add_argument("--journal", default=None)
    p.add_argument("--real", action="store_true")
    p = sp.add_parser("albero"); p.add_argument("--target"); p.add_argument("--out"); p.add_argument("--title", default="")
    p.add_argument("--check", default=None); p.add_argument("--show-junk", action="store_true")
    p = sp.add_parser("bench"); p.add_argument("--work", required=True); p.add_argument("--seed", type=int, default=42)
    p.add_argument("--scale", choices=["small", "medium"], default="small"); p.add_argument("--compare-ps", default=None)
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return
    if a.cmd == "albero" and not a.check and not (a.target and a.out):
        sys.exit("albero: servono --target e --out (oppure --check FILE)")
    {"env": cmd_env, "scan": cmd_scan, "dedup": cmd_dedup, "dedup-multi": cmd_dedup_multi, "execute": cmd_execute, "undo": cmd_undo,
     "albero": cmd_albero, "bench": cmd_bench}[a.cmd](a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
