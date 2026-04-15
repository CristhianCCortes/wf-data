#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enriquece Mods.json y Arcanes.json del snapshot con:
- subCategory (id estable)
- subCategory_es (label ES-419)
No altera name_es; solo agrega campos de clasificación.
"""

import os, json, re, datetime

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def norm(s):
    return (s or "").strip().lower()

# ---- Mods classification ----
def mod_subcat(it):
    compat = norm(it.get("compatName"))
    typ = norm(it.get("type"))
    cat = norm(it.get("category"))

    # Slots especiales (si aparecen explícitos)
    if "aura" in typ or "aura" in cat:
        return ("aura", "Aura")
    if "exilus" in typ or "exilus" in cat:
        return ("exilus", "Exilus")
    if "stance" in typ or "stance" in cat:
        return ("stance", "Postura")

    # Compatibilidad (ancla principal)
    if "warframe" in compat:
        return ("warframe", "Warframe")
    if "rifle" in compat or "primary" in compat or "shotgun" in compat:
        return ("primary", "Arma primaria")
    if "pistol" in compat or "secondary" in compat:
        return ("secondary", "Arma secundaria")
    if "melee" in compat:
        return ("melee", "Cuerpo a cuerpo")
    if "archwing" in compat:
        return ("archwing", "Archwing")
    if "arch-gun" in compat or "archgun" in compat:
        return ("archgun", "Arch Cañón")
    if "arch-melee" in compat or "archmelee" in compat:
        return ("archmelee", "Arch‑Melee")
    if any(x in compat for x in ["companion", "sentinel", "kubrow", "kavat", "pet"]):
        return ("companions", "Compañeros")

    return ("other", "Otros")

# ---- Arcanes classification ----
def arc_subcat(it):
    typ = norm(it.get("type"))
    un = (it.get("uniqueName") or "")
    blob = (typ + " " + un).lower()

    if "primary" in blob:
        return ("primary", "Arma primaria")
    if "secondary" in blob:
        return ("secondary", "Arma secundaria")
    if "melee" in blob:
        return ("melee", "Cuerpo a cuerpo")
    if "warframe" in blob:
        return ("warframe", "Warframe")
    if "operator" in blob or "amp" in blob:
        return ("operator
cd ~/Documents/WarframeProyecto/wf-data && \
cp tools/sync_de_es.py "tools/sync_de_es.backup_subcats_$(date +%Y%m%d_%H%M%S).py" && \
python3 - <<'PY'
from pathlib import Path

p = Path("tools/sync_de_es.py")
s = p.read_text(encoding="utf-8")

marker = "# __SUBCATEGORIES__"
if marker in s:
    print("OK: La inserción de subcategorías ya existe (no se duplicó).")
    raise SystemExit(0)

# Insertar justo después del bloque de extra sources si existe, si no, después de ensure_snapshot_copy(...)
anchor = "# __EXTRA_SOURCES__"
idx = s.find(anchor)

if idx != -1:
    # Insertamos después del try/except del extra sources (bloque completo)
    # Buscamos el final del try/except empezando desde el anchor, tomando el siguiente 'except' y la siguiente línea en blanco.
    tail = s[idx:]
    # Punto seguro: insertar antes de "Regenerando manifest.json..." si existe dentro de tail
    reg = tail.find('print("Regenerando manifest.json...')
    if reg == -1:
        # fallback: insertar después del bloque anchor (justo tras la línea anchor)
        insert_pos = idx
    else:
        insert_pos = idx + reg
else:
    # fallback: tras crear snapshot y copiar
    needle = "ensure_snapshot_copy(src_latest, target)"
    pos = s.find(needle)
    if pos == -1:
        raise SystemExit("No encontré ni __EXTRA_SOURCES__ ni ensure_snapshot_copy(...) para insertar el paso.")
    insert_pos = pos + len(needle)

insert_block = f"""

    {marker}
    # Enriquecer Mods/Arcanes con subCategory/subCategory_es (ES-419) dentro del snapshot actual
    try:
        import subprocess
        print("Enriqueciendo subcategorías (Mods/Arcanes)...")
        subprocess.check_call(["python3", "tools/enrich_subcategories.py"])
    except Exception as e:
        print("WARN: no se pudieron enriquecer subcategorías:", e)

"""

s2 = s[:insert_pos] + insert_block + s[insert_pos:]
p.write_text(s2, encoding="utf-8")
print("OK: sync_de_es.py ahora ejecuta enrich_subcategories.py en cada snapshot.")
