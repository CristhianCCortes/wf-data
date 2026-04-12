#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera fuentes adicionales desde exports del Public Export vía mirror.

Incluye:
- Amps: piezas modulares (Prism/Scaffold/Brace) detectadas por uniqueName con '/OperatorAmplifiers/'.
- Necramechs: detectados por uniqueName con '/EntratiMech/'.
- Zaws: piezas modulares Ostron detectadas por uniqueName con 'ModularMelee' (preferimos partes y evitamos '/Balance/').
- Kitguns: piezas modulares Solaris detectadas por uniqueName con '/InfKitGun/' o 'ModularGun' (preferimos partes y evitamos '/Balance/').

Escribe archivos JSON en sources/YYYY.MM.DD (UTC).
NOTA: El manifest lo regenera tools/sync_de_es.py.
"""

import os, json, datetime
from urllib.request import Request, urlopen

MIRROR_BASE = "https://raw.githubusercontent.com/calamity-inc/warframe-public-export/master/"
WEAPONS_ES = MIRROR_BASE + "ExportWeapons_es.json"
WARFRAMES_ES = MIRROR_BASE + "ExportWarframes_es.json"

SENTINELS_ES = MIRROR_BASE + "ExportSentinels_es.json"

# __PLUS_COMPANIONS_V1__
# Fuente más completa (warframe-public-export-plus)
PLUS_BASE = "https://raw.githubusercontent.com/calamity-inc/warframe-public-export-plus/senpai/"
PLUS_SENTINELS = PLUS_BASE + "ExportSentinels.json"

def iter_plus_items(root):
    # plus/ExportSentinels.json viene como dict (mapa)
    if isinstance(root, dict):
        return list(root.items())
    return []

def plus_blob(k, v):
    if not isinstance(v, dict):
        v = {}
    return " ".join([
        str(k or ""),
        str(v.get("uniqueName") or ""),
        str(v.get("name") or ""),
        str(v.get("productCategory") or ""),
        str(v.get("type") or ""),
        str(v.get("category") or ""),
        str(v.get("description") or ""),
    ]).lower()

def pick_plus(k, v):
    if not isinstance(v, dict):
        v = {}
    name = v.get("name") or k
    un = v.get("uniqueName") or k
    return {
        "name": name,
        "uniqueName": un,
        "productCategory": v.get("productCategory"),
        "description": v.get("description"),
    }

def build_moas_plus(items):
    out=[]
    for k,v in items:
        b = plus_blob(k,v)
        pc = (v.get("productCategory") if isinstance(v, dict) else None) or ""
        if ("moa" in b) or ("moapet" in b) or (pc.lower()=="moapets"):
            out.append(pick_plus(k,v))
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def build_hounds_plus(items):
    out=[]
    for k,v in items:
        b = plus_blob(k,v)
        pc = (v.get("productCategory") if isinstance(v, dict) else None) or ""
        # sabuesos: zanukapet / houndpets
        if ("zanukapet" in b) or ("hound" in b) or (pc.lower()=="houndpets"):
            out.append(pick_plus(k,v))
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def build_vulpaphylas_plus(items):
    out=[]
    for k,v in items:
        b = plus_blob(k,v)
        if ("vulp" in b) or ("vulpaphyla" in b) or ("infestedcat" in b):
            out.append(pick_plus(k,v))
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def build_predasites_plus(items):
    out=[]
    for k,v in items:
        b = plus_blob(k,v)
        if ("preda" in b) or ("predasite" in b) or ("infestedpredator" in b) or ("predatorkubrow" in b):
            out.append(pick_plus(k,v))
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def build_helminth_charger_plus(items):
    out=[]
    for k,v in items:
        b = plus_blob(k,v)
        # cargador helminth: charger + kubrowpet, sin mezclar predasite/vulp
        if ("/charger/kubrowpet/" in b) or ("chargerkubrowpetpowersuit" in b) or ("helminth" in b) or ("charger" in b):
            if ("preda" in b) or ("vulp" in b):
                continue
            out.append(pick_plus(k,v))
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def http_json(url: str):
    req = Request(url, headers={"User-Agent": "wf-data-extra/1.2"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Helpers ----------
def part_kind_from_unique_amp(un: str) -> str:
    un = un or ""
    if un.endswith("PrismPart"):
        return "Prisma"
    if un.endswith("ScaffoldPart"):
        return "Armazón"
    if un.endswith("BracePart"):
        return "Soporte"
    return "Parte"

def is_probable_part(un: str) -> bool:
    # Heurística genérica para “partes”: suele terminar en 'Part' o contener '/Parts/'
    un = un or ""
    return un.endswith("Part") or "/Parts/" in un or "\\Parts\\" in un

def is_balance_entry(un: str) -> bool:
    un = un or ""
    return "/Balance/" in un or "\\Balance\\" in un

def part_kind_from_unique_zaw(un: str) -> str:
    un = un or ""
    if "/Blades/" in un or "/Strikes/" in un:
        return "Golpe"
    if "/Handles/" in un or "/Grips/" in un:
        return "Empuñadura"
    if "/Links/" in un:
        return "Enlace"
    return "Parte"

def part_kind_from_unique_kitgun(un: str) -> str:
    un = un or ""
    if "/Barrels/" in un or "/Chambers/" in un:
        return "Cámara"
    if "/Grips/" in un:
        return "Empuñadura"
    if "/Chips/" in un or "/Loaders/" in un:
        return "Cargador"
    return "Parte"

# ---------- Builders ----------
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
            "partType": part_kind_from_unique_amp(un),
            "productCategory": o.get("productCategory"),
            "category": o.get("category"),
            "type": o.get("type"),
            "masteryReq": o.get("masteryReq"),
        })
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

def build_zaws(export_weapons_list):
    zaws = []
    for o in export_weapons_list:
        if not isinstance(o, dict):
            continue
        un = o.get("uniqueName") or ""
        if "ModularMelee" not in un:
            continue
        # Evitar entradas de balance y quedarse con partes reales
        if is_balance_entry(un):
            continue
        # Zaws: las piezas reales suelen estar en rutas /Handle/ y /Tip/ (no necesariamente terminan en "Part")
        if ("/Handle/" not in un) and ("/Tip/" not in un) and ("/Link/" not in un) and ("/Links/" not in un):
            continue
        zaws.append({
            "name": o.get("name"),
            "uniqueName": un,
            "partType": part_kind_from_unique_zaw(un),
            "productCategory": o.get("productCategory"),
            "category": o.get("category"),
            "type": o.get("type"),
            "masteryReq": o.get("masteryReq"),
        })
    order = {"Golpe": 1, "Empuñadura": 2, "Enlace": 3, "Parte": 9}
    zaws.sort(key=lambda x: (order.get(x.get("partType","Parte"), 9), (x.get("name") or "")))
    return zaws

def build_kitguns(export_weapons_list):
    kitguns = []
    for o in export_weapons_list:
        if not isinstance(o, dict):
            continue
        un = o.get("uniqueName") or ""
        if ("/InfKitGun/" not in un) and ("ModularGun" not in un):
            continue
        if is_balance_entry(un):
            continue
        if not is_probable_part(un):
            continue
        kitguns.append({
            "name": o.get("name"),
            "uniqueName": un,
            "partType": part_kind_from_unique_kitgun(un),
            "productCategory": o.get("productCategory"),
            "category": o.get("category"),
            "type": o.get("type"),
            "masteryReq": o.get("masteryReq"),
        })
    order = {"Cámara": 1, "Empuñadura": 2, "Cargador": 3, "Parte": 9}
    kitguns.sort(key=lambda x: (order.get(x.get("partType","Parte"), 9), (x.get("name") or "")))
    return kitguns


def build_sentinels(export_sentinels_list):
    out = []
    for o in export_sentinels_list:
        if not isinstance(o, dict):
            continue
        if (o.get("productCategory") or "") == "Sentinels":
            out.append({
                "name": o.get("name"),
                "uniqueName": o.get("uniqueName"),
                "productCategory": o.get("productCategory"),
                "description": o.get("description"),
                "excludeFromCodex": o.get("excludeFromCodex"),
            })
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def build_kubrows(export_sentinels_list):
    out = []
    for o in export_sentinels_list:
        if not isinstance(o, dict):
            continue

        pc = (o.get("productCategory") or "").strip()
        un = (o.get("uniqueName") or "")

        # Kubrows: el export usa rutas internas tipo /Lotus/Types/Game/KubrowPet/...
        # y suele terminar en ...KubrowPetPowerSuit.
        if not pc.lower().startswith("kubrow"):
            continue
        if ("/KubrowPet/" not in un) and ("KubrowPetPowerSuit" not in un):
            continue

        out.append({
            "name": o.get("name"),
            "uniqueName": un,
            "productCategory": pc,
            "description": o.get("description"),
            "excludeFromCodex": o.get("excludeFromCodex"),
        })

    out.sort(key=lambda x: (x.get("name") or ""))
    return out





def build_kavats_special(export_sentinels_list):
    # En este export vimos Venari/Venari Prime como Kavat (por uniqueName).
    out = []
    for o in export_sentinels_list:
        if not isinstance(o, dict):
            continue
        un = o.get("uniqueName") or ""
        if "/Kavat/" in un:
            out.append({
                "name": o.get("name"),
                "uniqueName": un,
                "productCategory": o.get("productCategory"),
                "description": o.get("description"),
                "excludeFromCodex": o.get("excludeFromCodex"),
            })
    out.sort(key=lambda x: (x.get("name") or ""))
    return out

def main(out_dir: str):
    ensure_dir(out_dir)

    weap_root = http_json(WEAPONS_ES)
    wfr_root  = http_json(WARFRAMES_ES)

    sent_root = http_json(SENTINELS_ES)


    export_weapons = weap_root.get("ExportWeapons", [])
    export_warframes = wfr_root.get("ExportWarframes", [])

    export_sentinels = sent_root.get("ExportSentinels", [])


    amps = build_amps(export_weapons)
    mechs = build_necramechs(export_warframes)
    zaws = build_zaws(export_weapons)
    kitguns = build_kitguns(export_weapons)

    write_json(os.path.join(out_dir, "Amps.json"), amps)
    write_json(os.path.join(out_dir, "Necramechs.json"), mechs)
    write_json(os.path.join(out_dir, "Zaws.json"), zaws)
    write_json(os.path.join(out_dir, "Kitguns.json"), kitguns)

    
    sentinels = build_sentinels(export_sentinels)
    kubrows = build_kubrows(export_sentinels)
    kavats = build_kavats_special(export_sentinels)

    write_json(os.path.join(out_dir, "Sentinels.json"), sentinels)
    write_json(os.path.join(out_dir, "Kubrows.json"), kubrows)
    write_json(os.path.join(out_dir, "Kavats.json"), kavats)

    
    # === PLUS companions ===
    plus_root = http_json(PLUS_SENTINELS)
    plus_items = iter_plus_items(plus_root)

    moas = build_moas_plus(plus_items)
    hounds = build_hounds_plus(plus_items)
    vulps = build_vulpaphylas_plus(plus_items)
    predas = build_predasites_plus(plus_items)
    charger = build_helminth_charger_plus(plus_items)

    write_json(os.path.join(out_dir, "MOAs.json"), moas)
    write_json(os.path.join(out_dir, "Hounds.json"), hounds)
    write_json(os.path.join(out_dir, "Vulpaphylas.json"), vulps)
    write_json(os.path.join(out_dir, "Predasites.json"), predas)
    write_json(os.path.join(out_dir, "HelminthCharger.json"), charger)
    print("OK: Generados en", out_dir)
    print(" - Amps.json:", len(amps))
    print(" - Necramechs.json:", len(mechs))
    print(" - Zaws.json:", len(zaws))
    print(" - Kitguns.json:", len(kitguns))
    print(" - Sentinels.json:", len(sentinels))
    print(" - Kubrows.json:", len(kubrows))
    print(" - Kavats.json:", len(kavats))
    print(" - MOAs.json:", len(moas))
    print(" - Hounds.json:", len(hounds))
    print(" - Vulpaphylas.json:", len(vulps))
    print(" - Predasites.json:", len(predas))
    print(" - HelminthCharger.json:", len(charger))

if __name__ == "__main__":
    today = datetime.datetime.utcnow().strftime("%Y.%m.%d")
    main(os.path.join("sources", today))
