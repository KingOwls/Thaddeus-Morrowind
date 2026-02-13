# src/bot/utils/artefact_gen.py
from __future__ import annotations

import random
import time
import uuid
from typing import Optional

COMMON_STATS = ["vida","ataque","poder_magico","armadura","resistencia_magica","probabilidad_critica","danio_critico"]

MAIN_TYPES = {
    "baston": ("vida", "plano"),
    "arma_artefacto": (["ataque","poder_magico"], "plano"),
    "caliz": (COMMON_STATS, "porcentaje"),
    "moneda": (["evasion","suerte","aura","inmortalidad","bloqueo","mana"], "mixed")
}

RARITY_MAIN_MULT = {1:1.00, 2:1.20, 3:1.40, 4:1.60, 5:1.80}
RARITY_SUB_MULT  = {1:1.00, 2:1.15, 3:1.30, 4:1.45, 5:1.60}

BASE_MAIN = {
    ("vida","plano"): 120,
    ("ataque","plano"): 12,
    ("poder_magico","plano"): 10,

    ("vida","porcentaje"): 0.08,
    ("ataque","porcentaje"): 0.06,
    ("poder_magico","porcentaje"): 0.06,
    ("armadura","porcentaje"): 0.07,
    ("resistencia_magica","porcentaje"): 0.07,
    ("probabilidad_critica","porcentaje"): 0.03,
    ("danio_critico","porcentaje"): 0.06,

    ("evasion","porcentaje"): 0.06,
    ("suerte","porcentaje"): 0.06,
    ("aura","porcentaje"): 0.06,
    ("inmortalidad","porcentaje"): 0.03,
    ("bloqueo","porcentaje"): 0.03,
    ("mana","plano"): 25
}

BASE_SUB = {
    ("vida","plano"): 30,
    ("ataque","plano"): 3,
    ("poder_magico","plano"): 3,
    ("armadura","plano"): 4,
    ("resistencia_magica","plano"): 4,

    ("vida","porcentaje"): 0.03,
    ("ataque","porcentaje"): 0.02,
    ("poder_magico","porcentaje"): 0.02,
    ("armadura","porcentaje"): 0.025,
    ("resistencia_magica","porcentaje"): 0.025,
    ("probabilidad_critica","porcentaje"): 0.01,
    ("danio_critico","porcentaje"): 0.02,

    ("mana","plano"): 8
}

def _roll_tipo(rng: random.Random) -> str:
    return "plano" if rng.random() < 0.55 else "porcentaje"

def generate_artefact(slot: str, rareza: int, seed: Optional[int] = None) -> dict:
    slot = str(slot).strip().lower()
    rareza = int(rareza)

    if slot not in MAIN_TYPES:
        raise ValueError(f"slot inválido: {slot}")
    if rareza not in {1,2,3,4,5}:
        raise ValueError(f"rareza inválida: {rareza}")

    seed = seed if seed is not None else int(time.time() * 1000)
    rng = random.Random(seed)

    # Main
    main_stat, main_tipo = MAIN_TYPES[slot]
    if slot == "arma_artefacto":
        main_stat = rng.choice(main_stat)
    elif slot == "caliz":
        main_stat = rng.choice(main_stat)
    elif slot == "moneda":
        main_stat = rng.choice(main_stat)
        main_tipo = "plano" if main_stat == "mana" else "porcentaje"

    base_main = BASE_MAIN[(main_stat, main_tipo)]
    main_val = base_main * RARITY_MAIN_MULT[rareza]

    subs = []
    used = set()

    def forbidden(stat: str, tipo: str) -> bool:
        key = f"{stat}:{tipo}"
        if slot == "baston" and key == "vida:plano":
            return True
        if slot == "arma_artefacto" and key in {"ataque:plano","poder_magico:plano"}:
            return True
        if slot == "caliz" and stat == main_stat:
            return True
        return False

    while len(subs) < 4:
        stat = rng.choice(COMMON_STATS)
        tipo = _roll_tipo(rng)

        if forbidden(stat, tipo):
            continue
        if (stat, tipo) in used:
            continue

        base_sub = BASE_SUB.get((stat, tipo))
        if base_sub is None:
            continue

        val = base_sub * RARITY_SUB_MULT[rareza]
        val = round(val, 4) if tipo == "porcentaje" else round(val, 2)

        used.add((stat, tipo))
        subs.append({"estadistica": stat, "tipo": tipo, "valor": val})

    return {
        "id": f"af_{uuid.uuid4().hex[:8]}",
        "slot": slot,
        "rareza": rareza,
        "nombre": f"{slot.title()} R{rareza}",
        "atributo_principal": {
            "estadistica": main_stat,
            "tipo": main_tipo,
            "valor": round(main_val, 4 if main_tipo == "porcentaje" else 2)
        },
        "atributos_secundarios": subs,
        "seed": seed
    }
