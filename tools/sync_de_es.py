#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_de_es.py (robusto)
- Intenta DE Public Export (B) primero: index_es.txt.lzma (origin) -> archivos hash (content).
- Si falla la descompresión/índice, usa fallback (A) a repo espejo actualizado automáticamente.
- Crea snapshot nuevo sources/YYYY.MM.DD/ copiando el último snapshot existente.
- Inyecta name_es en Mods.json y Arcanes/Arcanos.json usando uniqueName como llave.
- Regenera manifest.json.
"""

import os, json, hashlib, shutil, datetime
from urllib.request import urlopen, Request
import lzma

OWNER = "CristhianCCortes"
REPO = "wf-data"
BRANCH = "main"

# (B) DE Public Export
ORIGIN_INDEX = "https://origin.warframe.com/PublicExport/index_es.txt.lzma"
CONTENT_BASE = "https://content.warframe.com/PublicExport/Manifest/"
EXPORT_UPGRADES_PREFIX = "ExportUpgrades_es.json!"
EXPORT_RELIC_ARCANE_PREFIX = "ExportRelicArcane_es.json!"

# (A) Fallback espejo auto-actualizado (si falla DE)
# Repo: calamity-inc/warframe-public-export (archivos ExportUpgrades_es.json, ExportRelicArcane_es.json)
MIRROR_BASE = "https://raw.githubusercontent.com/calamity-inc/warframe-public-export/master/"
MIRROR_UPGRADES = MIRROR_BASE + "ExportUpgrades_es.json"
MIRROR_RELIC_ARCANE = MIRROR_BASE + "ExportRelicArcane_es.json"

def http_get_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "wf-data-sync/1.1"})
    with urlopen(req, timeout=60) as r:
        return r.read()

def try_decompress_lzma(data: bytes) -> str:
    # Algunos índices LZMA pueden venir en formato "ALONE" o con variaciones.
    # Probamos varios modos antes de rendirnos.
    for fmt in (lzma.FORMAT_AUTO, lzma.FORMAT_ALONE, lzma.FORMAT_XZ):
        try:
            return lzma.decompress(data, format=fmt).decode("utf-8", errors="replace")
        except Exception:
            pass
    raise RuntimeError("No se pudo descomprimir el índice LZMA con FORMAT_AUTO/ALONE/XZ.")

def find_manifest_line(index_text: str, prefix: str) -> str:
    for line in index_text.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line
    raise RuntimeError(f"No se encontró en el índice la entrada que empieza por: {prefix}")

def load_json_from_public_export(index_text: str, prefix: str) -> dict:
    manifest_line = find_manifest_line(index_text, prefix)
    url = CONTENT_BASE + manifest_line
    data = http_get_bytes(url)
    return json.loads(data.decode("utf-8", errors="replace"))

def load_json_from_mirror(url: str) -> dict:
    data = http_get_bytes(url)
    return json.loads(data.decode("utf-8", errors="replace"))

def collect_uniqueName_to_name(obj, out: dict):
    if isinstance(obj, dict):
        un = obj.get("uniqueName")
        nm = obj.get("name")
        if isinstance(un, str) and isinstance(nm, str) and nm.strip():
            out[un] = nm.strip()
        for v in obj.values():
            collect_uniqueName_to_name(v, out)
    elif isinstance(obj, list):
        for it in obj:
            collect_uniqueName_to_name(it, out)

def latest_sources_dir() -> str:
    base = "sources"
    if not os.path.isdir(base):
        raise RuntimeError("No existe la carpeta sources/")
    subdirs = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    if not subdirs:
        raise RuntimeError("No hay subcarpetas dentro de sources/")
    subdirs.sort()
    return os.path.join(base, subdirs[-1])

def ensure_snapshot_copy(src_dir: str, target_dir: str):
    if os.path.isdir(target_dir):
        return
    shutil.copytree(src_dir, target_dir)

def load_items_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data, data["items"], "dict_items"
    if isinstance(data, list):
        return data, data, "list"
    if isinstance(data, dict):
        vals = list(data.values())
        if all(isinstance(x, dict) for x in vals):
            return data, vals, "dict_values"
    return data, [], "unknown"

def save_items_json(original, items, mode, path: str):
    if mode == "dict_items":
        original["items"] = items
        out = original
    elif mode == "list":
        out = items
    elif mode == "dict_values":
        out = items
    else:
        out = original
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

def inject_spanish_names(file_path: str, name_map: dict) -> int:
    if not os.path.isfile(file_path):
        return 0
    original, items, mode = load_items_json(file_path)
    changed = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        un = it.get("uniqueName") or it.get("internalName") or it.get("id")
        if isinstance(un, str) and un in name_map:
            if "name_en" not in it and isinstance(it.get("name"), str):
                it["name_en"] = it["name"]
            it["name_es"] = name_map[un]
            changed += 1
    save_items_json(original, items, mode, file_path)
    return changed

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_manifest(sources_dir: str, generated_at: str) -> dict:
    files = [f for f in os.listdir(sources_dir) if f.lower().endswith(".json")]
    files.sort()
    sources = {}
    for fn in files:
        p = os.path.join(sources_dir, fn)
        size = os.path.getsize(p)
        sha = sha256_file(p)
        url = f"https://cdn.jsdelivr.net/gh/{OWNER}/{REPO}@{BRANCH}/{sources_dir.replace(os.sep,'/')}/{fn}"
        sources[fn] = {"version": generated_at, "url": url, "sha256": sha, "size": size}
    return {"schemaVersion": 1, "generatedAt": generated_at, "sources": sources}

def main():
    name_map = {}

    print("Intentando fuente primaria (DE Public Export) ...")
    try:
        idx_lzma = http_get_bytes(ORIGIN_INDEX)
        # sanity: índices suelen ser bastante más grandes; si es minúsculo, sospechamos
        if len(idx_lzma) < 5000:
            raise RuntimeError(f"Índice demasiado pequeño ({len(idx_lzma)} bytes).")
        idx_text = try_decompress_lzma(idx_lzma)

        upgrades_es = load_json_from_public_export(idx_text, EXPORT_UPGRADES_PREFIX)
        relic_arcane_es = load_json_from_public_export(idx_text, EXPORT_RELIC_ARCANE_PREFIX)

        collect_uniqueName_to_name(upgrades_es, name_map)
        collect_uniqueName_to_name(relic_arcane_es, name_map)

        print(f"✅ DE OK. Mapa creado con {len(name_map)} entradas.")
    except Exception as e:
        print(f"⚠️ DE falló ({e}). Usando fallback espejo (A) ...")
        upgrades_es = load_json_from_mirror(MIRROR_UPGRADES)
        relic_arcane_es = load_json_from_mirror(MIRROR_RELIC_ARCANE)
        collect_uniqueName_to_name(upgrades_es, name_map)
        collect_uniqueName_to_name(relic_arcane_es, name_map)
        print(f"✅ Mirror OK. Mapa creado con {len(name_map)} entradas.")

    src_latest = latest_sources_dir()
    today = datetime.datetime.utcnow().strftime("%Y.%m.%d")
    target = os.path.join("sources", today)

    print(f"Creando snapshot: {target} (copiando desde {src_latest})")
    ensure_snapshot_copy(src_latest, target)

    # __EXTRA_SOURCES__
    # Generar fuentes extra (Amps/Necramechs) dentro del snapshot actual
    try:
        import subprocess
        print("Generando fuentes extra (Amps/Necramechs)...")
        subprocess.check_call(["python3", "tools/build_extra_sources.py"])
    except Exception as e:
        # No bloqueamos todo si falla el extra; solo registramos el error
        print("WARN: no se pudieron generar fuentes extra:", e)


    candidates = [
        os.path.join(target, "Mods.json"),
        os.path.join(target, "Arcanes.json"),
        os.path.join(target, "Arcanos.json"),
    ]

    total_changed = 0
    for fp in candidates:
        ch = inject_spanish_names(fp, name_map)
        if ch:
            print(f"✔ {os.path.basename(fp)}: {ch} nombres ES aplicados")
        total_changed += ch

    print(f"Total de nombres ES aplicados Mods/Arcanos: {total_changed}")

    print("Regenerando manifest.json...")
    manifest = build_manifest(target, today)
    with open("manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("✅ Listo. Se actualizó sources/ y manifest.json.")

if __name__ == "__main__":
    main()
