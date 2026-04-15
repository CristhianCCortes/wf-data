#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enriquece Mods.json y Arcanes.json del snapshot con:
- subCategory (id estable)
- subCategory_es (label ES-419)

Uso:
  python3 tools/enrich_subcategories.py <snapshot_dir>
Si no se pasa snapshot_dir, usa sources/YYYY.MM.DD (UTC).
"""

import os, json, datetime, sys

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def to_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return list(x.values())
    return []

def norm(s):
    return (s or "").strip().lower()

def mod_subcat(it):
    compat = norm(it.get("compatName"))
    typ = norm(it.get("type"))
    cat = norm(it.get("category"))

    if "aura" in typ or "aura" in cat:
        return ("aura", "Aura")
    if "exilus" in typ or "exilus" in cat:
        return ("exilus", "Exilus")
    if "stance" in typ or "stance" in cat:
        return ("stance", "Postura")

    if "warframe" in compat:
        return ("warframe", "Warframe")

    if any(k in compat for k in ["rifle", "primary", "shotgun", "bow", "sniper"]):
        return ("primary", "Arma primaria")

    if any(k in compat for k in ["pistol", "secondary"]):
        return ("secondary", "Arma secundaria")

    if "melee" in compat:
        return ("melee", "Cuerpo a cuerpo")

    if "archwing" in compat:
        return ("archwing", "Archwing")
    if "arch-gun" in compat or "archgun" in compat:
        return ("archgun", "Arch Cañón")
    if "arch-melee" in compat or "archmelee" in compat:
        return ("archmelee", "Arch-Melee")

    if any(k in compat for k in ["companion", "sentinel", "kubrow", "kavat", "pet"]):
        return ("companions", "Compañeros")

    return ("other", "Otros")

def arc_subcat(it):
    typ = norm(it.get("type"))
    cat = norm(it.get("category"))
    un = (it.get("uniqueName") or "")
    blob = (typ + " " + cat + " " + un).lower()

    if "primary" in blob:
        return ("primary", "Arma primaria")
    if "secondary" in blob:
        return ("secondary", "Arma secundaria")
    if "melee" in blob:
        return ("melee", "Cuerpo a cuerpo")
    if "warframe" in blob:
        return ("warframe", "Warframe")
    if "operator" in blob or "amp" in blob:
        return ("operator_amp", "Operador / Amp")
    if "zaw" in blob:
        return ("zaw", "Zaws")
    if "kitgun" in blob:
        return ("kitgun", "Kitguns")
    if "companion" in blob or "pet" in blob or "sentinel" in blob:
        return ("companions", "Compañeros")
    if "necramech" in blob:
        return ("necramech", "Necramech")

    return ("other", "Otros")

def enrich_file(path, classifier):
    if not os.path.exists(path):
        print("WARN: no existe:", path)
        return 0

    data = load_json(path)
    arr = to_list(data)

    for it in arr:
        if isinstance(it, dict):
            sc, sc_es = classifier(it)
            it["subCategory"] = sc
            it["subCategory_es"] = sc_es

    save_json(path, arr)
    return len(arr)

def main(snapshot_dir):
    mods_path = os.path.join(snapshot_dir, "Mods.json")
    arcs_path = os.path.join(snapshot_dir, "Arcanes.json")

    n_mods = enrich_file(mods_path, mod_subcat)
    n_arcs = enrich_file(arcs_path, arc_subcat)

    print("OK: enriquecimiento subcategorías")
    print(" - Mods:", n_mods)
    print(" - Arcanes:", n_arcs)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        snapshot_dir = sys.argv[1]
    else:
        today = datetime.datetime.utcnow().strftime("%Y.%m.%d")
        snapshot_dir = os.path.join("sources", today)
    main(snapshot_dir)
