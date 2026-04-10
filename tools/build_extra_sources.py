#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera fuentes adicionales (Amps y Necramechs) desde exports del Public Export vía mirror.
- Amps: piezas modulares (Prism/Scaffold/Brace) detectadas por uniqueName con '/OperatorAmplifiers/'.
- Necramechs: detectados por uniqueName con '/EntratiMech/'.
Escribe archivos JSON en sources/YYYY.MM.DD (UTC) sin tocar manifest (eso lo hace sync_de_es.py).
"""

import os, json, datetime
from urllib.request import Request, urlopen

MIRROR_BASE = "https://raw.githubusercontent.com/calamity-inc/warframe-public-export/master/"
WEAPONS_ES = MIRROR_BASE + "ExportWeapons_es.json"
WARFRAMES_ES = MIRROR_BASE + "ExportWarframes_es.json"

def http_json(url: str):
    req = Request(url, headers={"User-Agent": "wf-data-extra/1.1"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def part_kind_from_unique(un: str) -> str:
    un = un or ""
    if un.endswith("PrismPart"):
        return "Prisma"
    if un.endswith("ScaffoldPart"):
        return "Armazón"
    if un.endswith("BracePart"):
        return "Soporte"
    return "Parte"

def build_amps(export_weapons_list):
    amps = []
    for o in export_weapons_list:
        if not isinstance(o, dict):
            continue
        un = o.get("uniqueName") or ""
        if "/OperatorAmplifiers/" not in un:
            continue
        amps.append({
            "name": o.get("name"),
            "uniqueName": un,
            "partType": part_kind_from_unique(un),
            "productCategory": o.get("productCategory"),
            "category": o.get("category"),
            "type": o.get("type"),
            "masteryReq": o.get("masteryReq"),
        })
    # Orden: primero por tipo de parte, luego por nombre
    order = {"Prisma": 1, "Armazón": 2, "Soporte": 3, "Parte": 9}
    amps.sort(key=lambda x: (order.get(x.get("partType","Parte"), 9), (x.get("name") or "")))
    return amps

def build_necramechs(export_warframes_list):
    mechs = []
    for o in export_warframes_list:
        if not isinstance(o, dict):
            continue
        un = o.get("uniqueName") or ""
        if "/EntratiMech/" not in un:
            continue
        mechs.append({
            "name": o.get("name"),
            "uniqueName": un,
            "productCategory": o.get("productCategory"),
            "category": o.get("category"),
            "type": o.get("type"),
            "masteryReq": o.get("masteryReq"),
        })
    mechs.sort(key=lambda x: (x.get("name") or ""))
    return mechs

def main(out_dir: str):
    ensure_dir(out_dir)

    weap_root = http_json(WEAPONS_ES)
    wfr_root  = http_json(WARFRAMES_ES)

    export_weapons = weap_root.get("ExportWeapons", [])
    export_warframes = wfr_root.get("ExportWarframes", [])

    amps = build_amps(export_weapons)
    mechs = build_necramechs(export_warframes)

    write_json(os.path.join(out_dir, "Amps.json"), amps)
    write_json(os.path.join(out_dir, "Necramechs.json"), mechs)

    # placeholders (próximo paso): Zaws / Kitguns
    # write_json(os.path.join(out_dir, "Zaws.json"), [])
    # write_json(os.path.join(out_dir, "Kitguns.json"), [])

    print("OK: Generados en", out_dir)
    print(" - Amps.json:", len(amps))
    print(" - Necramechs.json:", len(mechs))

if __name__ == "__main__":
    today = datetime.datetime.utcnow().strftime("%Y.%m.%d")
    main(os.path.join("sources", today))
