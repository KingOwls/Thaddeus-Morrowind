from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

print("✅ personaje.py fue importado")

# ============================================================
# Paths (robusto: relativo al archivo, no al working dir)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../src/bot/cogs
BOT_DIR = os.path.dirname(BASE_DIR)                    # .../src/bot
DATA_DIR = os.path.join(BOT_DIR, "data")               # .../src/bot/data

USERS_DIR = os.path.join(DATA_DIR, "users")            # .../src/bot/data/users

PATHWAY_DB = os.path.join(DATA_DIR, "pathways.json")
PROFESIONES_DB = os.path.join(DATA_DIR, "profesiones.json")
ROL_DB = os.path.join(DATA_DIR, "rol.json")

# Roles de staff permitidos para borrar/setear nivel/xp
STAFF_ROLE_NAMES = {"Staff", "Admin", "GM", "Moderador"}


# ============================================================
# Helpers I/O
# ============================================================
def _ensure_dirs() -> None:
    os.makedirs(USERS_DIR, exist_ok=True)

def _can_create_more(root: Dict[str, Any]) -> Tuple[bool, str]:
    current = len(root.get("personajes", {}))
    if current >= 4:
        return False, "🚫 Este usuario ya tiene el máximo de 4 personajes."
    return True, ""

def _read_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _user_file(user_id: int) -> str:
    return os.path.join(USERS_DIR, f"{user_id}.json")


def _load_user(user_id: int) -> Dict[str, Any]:
    _ensure_dirs()
    path = _user_file(user_id)
    data = _read_json(path)
    if not data:
        data = {str(user_id): {"personajes": {}}}
        _write_json(path, data)
    return data


def _save_user(user_id: int, data: Dict[str, Any]) -> None:
    _ensure_dirs()
    _write_json(_user_file(user_id), data)


def _get_user_root(data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    key = str(user_id)
    if key not in data:
        data[key] = {"personajes": {}}
    if "personajes" not in data[key]:
        data[key]["personajes"] = {}
    return data[key]


def _get_character(data: Dict[str, Any], user_id: int, nombre_personaje: str) -> Optional[Dict[str, Any]]:
    root = _get_user_root(data, user_id)
    return root["personajes"].get(nombre_personaje)


def _is_staff(member: discord.Member) -> bool:
    role_names = {r.name for r in member.roles}
    return len(role_names.intersection(STAFF_ROLE_NAMES)) > 0


# ============================================================
# DB loaders (roles/profesiones/pathways)
# ============================================================
def _load_db(path: str) -> Dict[str, Any]:
    data = _read_json(path)
    return data if isinstance(data, dict) else {}


def _db_block(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    block = data.get(key)
    return block if isinstance(block, dict) else {}


def _normalize_label(s: str) -> str:
    return " ".join(str(s).strip().split())


def _load_options(path: str) -> List[str]:
    """
    Devuelve lista de NOMBRES human-friendly:
    - rol.json: {"roles": {"guerrero": {"nombre": "Guerrero", ...}, ...}}
    - profesiones.json: {"profesiones": {"cocinero": {"nombre": "Cocinero", ...}, ...}}
    - pathways.json: {"pathways": {"The Fool": {"nombre":"The Fool", ...}, ...}}
    """
    data = _load_db(path)
    if not data:
        return []

    if "roles" in data:
        roles = _db_block(data, "roles")
        return [_normalize_label(v.get("nombre", k)) for k, v in roles.items() if isinstance(v, dict)]

    if "profesiones" in data:
        profs = _db_block(data, "profesiones")
        return [_normalize_label(v.get("nombre", k)) for k, v in profs.items() if isinstance(v, dict)]

    if "pathways" in data:
        paths = _db_block(data, "pathways")
        return [_normalize_label(v.get("nombre", k)) for k, v in paths.items() if isinstance(v, dict)]

    # fallback: dict plano
    return [_normalize_label(k) for k in data.keys()]

def _db_lookup_by_display_name(db_path: str, display_name: str) -> Optional[Dict[str, Any]]:
    """
    Busca un entry en rol/profesiones/pathways comparando por 'nombre' (o key fallback)
    y devuelve el dict completo (donde viene 'imagen', 'descripcion', etc).
    """
    data = _load_db(db_path)
    target = _normalize_label(display_name).lower()

    # roles
    if "roles" in data:
        block = _db_block(data, "roles")
        for k, v in block.items():
            if not isinstance(v, dict):
                continue
            nm = _normalize_label(v.get("nombre", k)).lower()
            if nm == target:
                return v

    # profesiones
    if "profesiones" in data:
        block = _db_block(data, "profesiones")
        for k, v in block.items():
            if not isinstance(v, dict):
                continue
            nm = _normalize_label(v.get("nombre", k)).lower()
            if nm == target:
                return v

    # pathways
    if "pathways" in data:
        block = _db_block(data, "pathways")
        for k, v in block.items():
            if not isinstance(v, dict):
                continue
            nm = _normalize_label(v.get("nombre", k)).lower()
            if nm == target:
                return v

    return None


def _safe_image_url(entry: Optional[Dict[str, Any]]) -> Optional[str]:
    if not entry or not isinstance(entry, dict):
        return None
    url = entry.get("imagen")
    if isinstance(url, str) and url.startswith("http"):
        return url
    return None


def _safe_desc(entry: Optional[Dict[str, Any]], limit: int = 250) -> str:
    if not entry or not isinstance(entry, dict):
        return ""
    desc = entry.get("descripcion")
    if not isinstance(desc, str):
        return ""
    desc = desc.strip()
    if len(desc) > limit:
        desc = desc[: limit - 3] + "..."
    return desc


def _find_role_by_name(role_name: str) -> Optional[Dict[str, Any]]:
    db = _load_db(ROL_DB)
    roles = _db_block(db, "roles")
    for k, v in roles.items():
        if not isinstance(v, dict):
            continue
        nombre = _normalize_label(v.get("nombre", k))
        if nombre.lower() == _normalize_label(role_name).lower():
            return v
    return None


# ============================================================
# Base template
# ============================================================
def _base_stats(recurso_tipo: str = "Mana") -> Dict[str, Any]:
    return {
        "vida": {"base": 100, "escalado_base": "vida"},
        "ataque": {"base": 10, "escalado_base": "ataque"},
        "poder_magico": {"base": 5, "escalado_base": "poder_magico"},
        "armadura": {"base": 0, "escalado_base": "armadura"},
        "resistencia_magica": {"base": 0, "escalado_base": "resistencia_magica"},
        "probabilidad_critica": {"base": 0.05, "escalado_base": "probabilidad_critica"},
        "danio_critico": {"base": 1.5, "escalado_base": "danio_critico"},
        "recurso": {"tipo": recurso_tipo, "cantidad_maxima": {"base": 50, "escalado_base": "recurso.cantidad_maxima"}},
        "evasion": {"base": 0.0, "escalado_base": "evasion"},
        "suerte": {"base": 0, "escalado_base": "suerte"},
        "aura": {"base": 0, "escalado_base": "aura"},
        "inmortalidad": {"base": 0.0, "escalado_base": "inmortalidad"},
        "bloqueo": {"base": 0.0, "escalado_base": "bloqueo"},
    }


def _base_skills() -> Dict[str, Any]:
    return {
        "ataque_basico": {
            "nombre": "Golpe Básico",
            "descripcion": "Un ataque simple.",
            "tipo": "Activa",
            "costo": {"tipo": "None", "valor": 0},
            "escalado": {"estadistica_base": "ataque", "multiplicador": 1.0},
            "bonificadores": {"bono_danio": 0.0, "bono_curacion": 0.0},
        },
        "habilidad_bloqueo": {
            "nombre": "Bloqueo",
            "descripcion": "Aumenta la probabilidad de bloquear por un tiempo.",
            "tipo": "Activa",
            "costo": {"tipo": "CD", "valor": 10},
            "efecto": {"bono_bloqueo": 0.1, "duracion": 5},
        },
        "habilidades_aprendibles": [],
    }


def _empty_equipment() -> Dict[str, Any]:
    return {
        "artefactos": {"caliz": None, "moneda": None, "arma_artefacto": None, "baston": None},
        "arma_principal": None,
    }


def _new_character(nombre: str, apodo: str, rol: str, profesion: str, nacion: str) -> Dict[str, Any]:
    role_def = _find_role_by_name(rol) or {}
    recurso_def = role_def.get("recurso_por_defecto") if isinstance(role_def.get("recurso_por_defecto"), dict) else {}
    recurso_tipo = str(recurso_def.get("tipo", "Mana"))

    ch = {
        "apodo": apodo,
        "nombre": nombre,
        "nivel": 1,
        "experiencia": 0,
        "estadisticas": _base_stats(recurso_tipo=recurso_tipo),
        "kit_habilidades": _base_skills(),
        "equipamiento": _empty_equipment(),
        "arboles_habilidad": {
            "rol": {"nombre": rol, "nivel": 0, "experiencia": 0},
            "profesion": {"nombre": profesion, "nivel": 0, "experiencia": 0},
            "nacion": {"nombre": nacion, "nivel": 0, "experiencia": 0},
        },
        "inventario": [],
        "dinero": {
            "efectivo": 0,
            "cuenta": 0,
        },

        # meta opcional para depurar
        "meta": {
            "rol_key": role_def.get("nombre", rol),
        },
    }
    return ch


# ============================================================
# Stat computation (base + flat + percent)
# ============================================================
STAT_KEYS = [
    "vida",
    "ataque",
    "poder_magico",
    "armadura",
    "resistencia_magica",
    "probabilidad_critica",
    "danio_critico",
    "evasion",
    "suerte",
    "aura",
    "inmortalidad",
    "bloqueo",
]
NESTED_STAT_KEYS = ["recurso.cantidad_maxima"]


def _get_stat_value(stats: Dict[str, Any], key: str) -> float:
    if key == "recurso.cantidad_maxima":
        return float(stats["recurso"]["cantidad_maxima"]["base"])
    return float(stats[key]["base"])


def _set_stat_value(stats: Dict[str, Any], key: str, new_base: float) -> None:
    if key == "recurso.cantidad_maxima":
        stats["recurso"]["cantidad_maxima"]["base"] = float(new_base)
    else:
        stats[key]["base"] = float(new_base)


def _add_to_acc(acc: Dict[str, float], key: str, value: float) -> None:
    acc[key] = float(acc.get(key, 0.0)) + float(value)


def _collect_item_bonuses(item: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Retorna (flat, pct) desde:
    - atributo_principal
    - atributos_secundarios (max 3)
    tipo: plano|porcentaje
    pct se guarda como fracción (0.10 = +10%)
    """
    flat: Dict[str, float] = {}
    pct: Dict[str, float] = {}

    def apply_attr(attr: Dict[str, Any]) -> None:
        stat = attr.get("estadistica")
        tipo = attr.get("tipo")
        val = attr.get("valor", 0)
        if not stat or tipo not in {"plano", "porcentaje"}:
            return
        if tipo == "plano":
            _add_to_acc(flat, stat, float(val))
        else:
            _add_to_acc(pct, stat, float(val))

    if isinstance(item.get("atributo_principal"), dict):
        apply_attr(item.get("atributo_principal", {}))

    for a in item.get("atributos_secundarios", [])[:3]:
        if isinstance(a, dict):
            apply_attr(a)

    return flat, pct


def _compute_stats(character: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    - base = stats.base + flat(arma_principal) + flat(artefactos)
    - adicionales = percent(artefactos + arma_principal) aplicados sobre base
    - total = base + adicionales
    """
    stats = character["estadisticas"]
    equip = character["equipamiento"]

    base_vals: Dict[str, float] = {k: _get_stat_value(stats, k) for k in STAT_KEYS}
    base_vals["recurso.cantidad_maxima"] = _get_stat_value(stats, "recurso.cantidad_maxima")

    flat_bonus: Dict[str, float] = {}
    pct_bonus: Dict[str, float] = {}

    weapon = equip.get("arma_principal")
    if isinstance(weapon, dict):
        f, p = _collect_item_bonuses(weapon)
        for kk, vv in f.items():
            _add_to_acc(flat_bonus, kk, vv)
        for kk, vv in p.items():
            _add_to_acc(pct_bonus, kk, vv)

    for _, item in (equip.get("artefactos") or {}).items():
        if isinstance(item, dict):
            f, p = _collect_item_bonuses(item)
            for kk, vv in f.items():
                _add_to_acc(flat_bonus, kk, vv)
            for kk, vv in p.items():
                _add_to_acc(pct_bonus, kk, vv)

    computed_base: Dict[str, float] = dict(base_vals)
    for kk, vv in flat_bonus.items():
        _add_to_acc(computed_base, kk, vv)

    adicionales: Dict[str, float] = {}
    for kk, pct in pct_bonus.items():
        base_for = float(computed_base.get(kk, 0.0))
        _add_to_acc(adicionales, kk, base_for * float(pct))

    total: Dict[str, float] = dict(computed_base)
    for kk, vv in adicionales.items():
        _add_to_acc(total, kk, vv)

    return {"base": computed_base, "adicionales": adicionales, "total": total}


# ============================================================
# Leveling using rol.json (mejora_atributos_por_nivel)
# ============================================================
def _apply_role_leveling(ch: Dict[str, Any], old_level: int, new_level: int) -> None:
    """
    Aplica incrementos por nivel del rol (mejora_atributos_por_nivel) en la estadística BASE del personaje.
    Solo aplica si new_level > old_level.
    """
    if new_level <= old_level:
        return

    rol_name = (ch.get("arboles_habilidad", {}).get("rol", {}) or {}).get("nombre")
    if not rol_name:
        return

    role_def = _find_role_by_name(str(rol_name))
    if not role_def:
        return

    inc = role_def.get("mejora_atributos_por_nivel")
    if not isinstance(inc, dict):
        return

    stats = ch.get("estadisticas", {})
    levels_gained = new_level - old_level

    for k, per_level in inc.items():
        try:
            per_level_val = float(per_level)
        except Exception:
            continue

        # Permitir nested
        if k == "recurso.cantidad_maxima":
            base_now = _get_stat_value(stats, "recurso.cantidad_maxima")
            _set_stat_value(stats, "recurso.cantidad_maxima", base_now + per_level_val * levels_gained)
            continue

        # Normal stats
        if k in stats and isinstance(stats.get(k), dict) and "base" in stats[k]:
            base_now = float(stats[k]["base"])
            stats[k]["base"] = base_now + per_level_val * levels_gained


# ============================================================
# UI: drafts + Modal + Selects (Slash) + Buttons (Prefix)
# ============================================================
@dataclass
class CreateDraft:
    nombre: str
    apodo: str
    rol: Optional[str] = None
    profesion: Optional[str] = None
    nacion: Optional[str] = None


class CreateCharacterModal(discord.ui.Modal, title="Crear Personaje"):
    nombre = discord.ui.TextInput(label="Nombre del personaje", max_length=32)
    apodo = discord.ui.TextInput(label="Apodo (único)", max_length=32)

    def __init__(self, cog: "PersonajeCog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        nombre = str(self.nombre.value).strip()
        apodo = str(self.apodo.value).strip()

        if not nombre or not apodo:
            await interaction.response.send_message("Nombre y apodo son obligatorios.", ephemeral=True)
            return

        draft = CreateDraft(nombre=nombre, apodo=apodo)
        view = CreateTreeSelectView(self.cog, draft)
        await interaction.response.send_message(
            "Selecciona **Rol**, **Profesión** y **Nación**:",
            view=view,
            ephemeral=True,
        )


class CreateTreeSelectView(discord.ui.View):
    def __init__(self, cog: "PersonajeCog", draft: CreateDraft):
        super().__init__(timeout=180)
        self.cog = cog
        self.draft = draft

        rol_opts = _load_options(ROL_DB)
        prof_opts = _load_options(PROFESIONES_DB)
        nac_opts = _load_options(PATHWAY_DB)

        self.rol_select.options = [discord.SelectOption(label=o) for o in rol_opts[:25]]
        self.profesion_select.options = [discord.SelectOption(label=o) for o in prof_opts[:25]]
        self.nacion_select.options = [discord.SelectOption(label=o) for o in nac_opts[:25]]

    @discord.ui.select(placeholder="Elige Rol", min_values=1, max_values=1, options=[])
    async def rol_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.draft.rol = select.values[0]
        await interaction.response.send_message(f"Rol seleccionado: **{self.draft.rol}**", ephemeral=True)

    @discord.ui.select(placeholder="Elige Profesión", min_values=1, max_values=1, options=[])
    async def profesion_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.draft.profesion = select.values[0]
        await interaction.response.send_message(f"Profesión seleccionada: **{self.draft.profesion}**", ephemeral=True)

    @discord.ui.select(placeholder="Elige Nación", min_values=1, max_values=1, options=[])
    async def nacion_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.draft.nacion = select.values[0]
        await interaction.response.send_message(f"Nación seleccionada: **{self.draft.nacion}**", ephemeral=True)

    @discord.ui.button(label="Crear personaje", style=discord.ButtonStyle.green)
    async def create_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not (self.draft.rol and self.draft.profesion and self.draft.nacion):
            await interaction.response.send_message("Te faltan selecciones: Rol/Profesión/Nación.", ephemeral=True)
            return

        ok, msg = self.cog.create_character_for_user(
            user_id=interaction.user.id,
            nombre=self.draft.nombre,
            apodo=self.draft.apodo,
            rol=self.draft.rol,
            profesion=self.draft.profesion,
            nacion=self.draft.nacion,
        )
        await interaction.response.send_message(msg, ephemeral=True)
        self.stop()


class CreateTreeButtonsView(discord.ui.View):
    """
    Para prefijo (=): selección por BOTONES (izq/der/aceptar/saltar).
    Se usa en 3 etapas: Rol -> Profesión -> Nación
    """
    def __init__(self, cog: "PersonajeCog", draft: CreateDraft, stage: str):
        super().__init__(timeout=180)
        self.cog = cog
        self.draft = draft
        self.stage = stage  # "rol" | "profesion" | "nacion"
        self.index = 0

        if stage == "rol":
            self.options = _load_options(ROL_DB)
        elif stage == "profesion":
            self.options = _load_options(PROFESIONES_DB)
        else:
            self.options = _load_options(PATHWAY_DB)

        if not self.options:
            self.options = ["(Sin opciones)"]

    def _current(self) -> str:
        if not self.options:
            return "(Sin opciones)"
        self.index = max(0, min(self.index, len(self.options) - 1))
        return self.options[self.index]

    def _embed(self) -> discord.Embed:
        title_map = {"rol": "Rol", "profesion": "Profesión", "nacion": "Nación"}
        title = title_map.get(self.stage, self.stage)
        cur = self._current()

        # Elegir DB según stage
        if self.stage == "rol":
            entry = _db_lookup_by_display_name(ROL_DB, cur)
        elif self.stage == "profesion":
            entry = _db_lookup_by_display_name(PROFESIONES_DB, cur)
        else:
            entry = _db_lookup_by_display_name(PATHWAY_DB, cur)

        desc = _safe_desc(entry)
        e = discord.Embed(
            title=f"Selecciona {title}",
            description=f"**{cur}**\n{desc}\n\n({self.index+1}/{len(self.options)})"
        )
        e.set_footer(text="Usa ◀ ▶ para cambiar, ✅ para aceptar, ⏭ para 'no quiero ninguna'")

        img = _safe_image_url(entry)
        if img:
            e.set_thumbnail(url=img)  # thumbnail es más estable/bonito para navegación

        return e

    

    async def _update_message(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def left_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.index = (self.index - 1) % len(self.options)
        await self._update_message(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def right_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.index = (self.index + 1) % len(self.options)
        await self._update_message(interaction)

    @discord.ui.button(label="✅", style=discord.ButtonStyle.green)
    async def accept_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        val = self._current()
        if self.stage == "rol":
            self.draft.rol = val
            next_stage = "profesion"
        elif self.stage == "profesion":
            self.draft.profesion = val
            next_stage = "nacion"
        else:
            self.draft.nacion = val
            next_stage = ""

        if next_stage:
            view = CreateTreeButtonsView(self.cog, self.draft, next_stage)
            await interaction.response.edit_message(embed=view._embed(), view=view)
            return

        # ya tiene las 3
        ok, msg = self.cog.create_character_for_user(
            user_id=interaction.user.id,
            nombre=self.draft.nombre,
            apodo=self.draft.apodo,
            rol=self.draft.rol or "Sin Rol",
            profesion=self.draft.profesion or "Sin Profesión",
            nacion=self.draft.nacion or "Sin Nación",
        )
        await interaction.response.edit_message(content=msg, embed=None, view=None)
        self.stop()

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.danger)
    async def skip_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        # “No quiero ninguna”: guarda "Sin X"
        if self.stage == "rol":
            self.draft.rol = "Sin Rol"
            next_stage = "profesion"
        elif self.stage == "profesion":
            self.draft.profesion = "Sin Profesión"
            next_stage = "nacion"
        else:
            self.draft.nacion = "Sin Nación"
            next_stage = ""

        if next_stage:
            view = CreateTreeButtonsView(self.cog, self.draft, next_stage)
            await interaction.response.edit_message(embed=view._embed(), view=view)
            return

        ok, msg = self.cog.create_character_for_user(
            user_id=interaction.user.id,
            nombre=self.draft.nombre,
            apodo=self.draft.apodo,
            rol=self.draft.rol or "Sin Rol",
            profesion=self.draft.profesion or "Sin Profesión",
            nacion=self.draft.nacion or "Sin Nación",
        )
        await interaction.response.edit_message(content=msg, embed=None, view=None)
        self.stop()


# ============================================================
# Cog
# ============================================================
class PersonajeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    # ---------- CRUD ----------
    def create_character_for_user(
        self,
        user_id: int,
        nombre: str,
        apodo: str,
        rol: str,
        profesion: str,
        nacion: str,
    ) -> Tuple[bool, str]:
        data = _load_user(user_id)
        root = _get_user_root(data, user_id)

        if nombre in root["personajes"]:
            return False, f"Ya tienes un personaje llamado **{nombre}**."

        for _, c in root["personajes"].items():
            if isinstance(c, dict) and c.get("apodo") == apodo:
                return False, f"El apodo **{apodo}** ya lo usas en otro personaje."

        root["personajes"][nombre] = _new_character(nombre, apodo, rol, profesion, nacion)
        _save_user(user_id, data)
        return True, f"✅ Personaje **{nombre}** creado con apodo **{apodo}**."

    def must_get_character(
        self, user_id: int, nombre: Optional[str]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
        data = _load_user(user_id)
        root = _get_user_root(data, user_id)

        if not root["personajes"]:
            return None, None, "No tienes personaje. Usa `/pj crear` o `=pj crear <Nombre> <Apodo>`."

        if not nombre:
            nombre = next(iter(root["personajes"].keys()))

        ch = root["personajes"].get(nombre)
        if not ch:
            return None, None, f"No encontré el personaje **{nombre}**."
        return ch, nombre, ""

    def update_character(self, user_id: int, nombre: str, new_ch: Dict[str, Any]) -> None:
        data = _load_user(user_id)
        root = _get_user_root(data, user_id)
        root["personajes"][nombre] = new_ch
        _save_user(user_id, data)

    # ---------- Embeds ----------
    def basic_embed(self, nombre: str, ch: Dict[str, Any]) -> discord.Embed:
        trees = ch.get("arboles_habilidad", {})
        rol = trees.get("rol", {})
        prof = trees.get("profesion", {})
        nac = trees.get("nacion", {})
        money = ch.get("dinero", {})
        ef = int(money.get("efectivo", 0))
        cu = int(money.get("cuenta", 0))
        tot = ef + cu
        e.add_field(name="💰 Dinero", value=f"Efectivo: **{ef}**\nCuenta: **{cu}**\nTotal: **{tot}**", inline=False)


        e = discord.Embed(title=f"📌 {ch.get('nombre', nombre)} ({ch.get('apodo', '-')})")
        e.add_field(name="Nivel", value=str(ch.get("nivel", 1)), inline=True)
        e.add_field(name="Experiencia", value=str(ch.get("experiencia", 0)), inline=True)

        e.add_field(name="Rol", value=f"{rol.get('nombre','-')} | Nv {rol.get('nivel',0)}", inline=False)
        e.add_field(name="Profesión", value=f"{prof.get('nombre','-')} | Nv {prof.get('nivel',0)}", inline=False)
        e.add_field(name="Nación", value=f"{nac.get('nombre','-')} | Nv {nac.get('nivel',0)}", inline=False)
        return e

    def stats_embed(self, ch: Dict[str, Any]) -> discord.Embed:
        calc = _compute_stats(ch)
        base = calc["base"]
        add = calc["adicionales"]
        total = calc["total"]

        e = discord.Embed(title="📊 Estadísticas")

        def fmt(k: str) -> str:
            b = base.get(k, 0.0)
            a = add.get(k, 0.0)
            t = total.get(k, 0.0)
            return f"Base: **{b:.2f}** | 🟦 Extra: **{a:.2f}** | Total: **{t:.2f}**"

        lines = []
        for k in STAT_KEYS:
            lines.append(f"**{k}**\n{fmt(k)}")
        lines.append(f"**recurso.cantidad_maxima**\n{fmt('recurso.cantidad_maxima')}")

        e.add_field(name="Stats (1)", value="\n\n".join(lines[:6]), inline=False)
        e.add_field(name="Stats (2)", value="\n\n".join(lines[6:12]), inline=False)
        e.add_field(name="Stats (3)", value="\n\n".join(lines[12:]), inline=False)
        return e

    # ============================================================
    # SLASH GROUPS
    # ============================================================
    pj = app_commands.Group(name="pj", description="Comandos de personaje")
    staff = app_commands.Group(name="pj_staff", description="Comandos de staff (GM/Admin)")

    @pj.command(name="crear", description="Crea tu personaje con una interfaz (modal + selects).")
    async def pj_crear(self, interaction: discord.Interaction):
        data = _load_user(interaction.user.id)
        root = _get_user_root(data, interaction.user.id)
        if root["personajes"]:
            await interaction.response.send_message(
                "Ya tienes un personaje. (Si quieres multi-personaje, lo habilitamos.)",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(CreateCharacterModal(self))
    
    @pj.command(name="ver", description="Ver tu personaje (basica o estadisticas).")
    @app_commands.describe(vista="basica | estadisticas", nombre="Nombre del personaje (opcional)")
    async def pj_ver(self, interaction: discord.Interaction, vista: str, nombre: Optional[str] = None):
        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        vista = vista.lower().strip()
        if vista == "basica":
            e = self.basic_embed(cname, ch)
        elif vista == "estadisticas":
            e = self.stats_embed(ch)
        else:
            await interaction.response.send_message("Vista inválida. Usa `basica` o `estadisticas`.", ephemeral=True)
            return

        await interaction.response.send_message(embed=e, ephemeral=True)

    @pj.command(name="equipar_artefacto", description="Equipa un artefacto en un slot (pegas JSON del item).")
    @app_commands.describe(slot="caliz | moneda | arma_artefacto | baston", item_json="JSON del item")
    async def pj_equipar_artefacto(self, interaction: discord.Interaction, slot: str, item_json: str, nombre: Optional[str] = None):
        slot = slot.lower().strip()
        if slot not in {"caliz", "moneda", "arma_artefacto", "baston"}:
            await interaction.response.send_message("Slot inválido.", ephemeral=True)
            return

        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        try:
            item = json.loads(item_json)
            if not isinstance(item, dict):
                raise ValueError
        except Exception:
            await interaction.response.send_message("El `item_json` no es un JSON válido (objeto).", ephemeral=True)
            return

        ch["equipamiento"]["artefactos"][slot] = item
        self.update_character(interaction.user.id, cname, ch)
        await interaction.response.send_message(f"✅ Artefacto equipado en **{slot}**.", ephemeral=True)

    @pj.command(name="quitar_artefacto", description="Quita el artefacto de un slot.")
    @app_commands.describe(slot="caliz | moneda | arma_artefacto | baston")
    async def pj_quitar_artefacto(self, interaction: discord.Interaction, slot: str, nombre: Optional[str] = None):
        slot = slot.lower().strip()
        if slot not in {"caliz", "moneda", "arma_artefacto", "baston"}:
            await interaction.response.send_message("Slot inválido.", ephemeral=True)
            return

        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        ch["equipamiento"]["artefactos"][slot] = None
        self.update_character(interaction.user.id, cname, ch)
        await interaction.response.send_message(f"✅ Quitado artefacto de **{slot}**.", ephemeral=True)

    @pj.command(name="equipar_arma", description="Equipa el arma principal (pegas JSON del arma).")
    @app_commands.describe(item_json="JSON del arma principal")
    async def pj_equipar_arma(self, interaction: discord.Interaction, item_json: str, nombre: Optional[str] = None):
        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        try:
            item = json.loads(item_json)
            if not isinstance(item, dict):
                raise ValueError
        except Exception:
            await interaction.response.send_message("El `item_json` no es un JSON válido (objeto).", ephemeral=True)
            return

        ch["equipamiento"]["arma_principal"] = item
        self.update_character(interaction.user.id, cname, ch)
        await interaction.response.send_message("✅ Arma principal equipada.", ephemeral=True)

    @pj.command(name="quitar_arma", description="Quita el arma principal.")
    async def pj_quitar_arma(self, interaction: discord.Interaction, nombre: Optional[str] = None):
        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        ch["equipamiento"]["arma_principal"] = None
        self.update_character(interaction.user.id, cname, ch)
        await interaction.response.send_message("✅ Arma principal quitada.", ephemeral=True)

    @pj.command(name="habilidad_agregar", description="Agrega una habilidad aprendible.")
    async def pj_habilidad_agregar(
        self,
        interaction: discord.Interaction,
        nombre_habilidad: str,
        descripcion: str,
        tipo: str,
        costo_tipo: str,
        costo_valor: int,
        estadistica_base: str,
        multiplicador: float,
        nombre: Optional[str] = None,
    ):
        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        tipo = tipo.strip().capitalize()
        if tipo not in {"Activa", "Pasiva"}:
            await interaction.response.send_message("Tipo inválido (Activa/Pasiva).", ephemeral=True)
            return

        new_skill = {
            "nombre": nombre_habilidad,
            "descripcion": descripcion,
            "tipo": tipo,
            "nivel_habilidad": 1,
            "costo": {"tipo": costo_tipo, "valor": int(costo_valor)},
            "canalizacion_segundos": 0,
            "escalado": {"estadistica_base": estadistica_base, "multiplicador": float(multiplicador)},
            "bonificadores": {"bono_danio": 0.0, "bono_curacion": 0.0},
        }

        skills = ch["kit_habilidades"].get("habilidades_aprendibles", [])
        if any(isinstance(s, dict) and s.get("nombre") == nombre_habilidad for s in skills):
            await interaction.response.send_message("Ya tienes una habilidad con ese nombre.", ephemeral=True)
            return

        skills.append(new_skill)
        ch["kit_habilidades"]["habilidades_aprendibles"] = skills
        self.update_character(interaction.user.id, cname, ch)
        await interaction.response.send_message(f"✅ Habilidad **{nombre_habilidad}** agregada.", ephemeral=True)

    @pj.command(name="habilidad_quitar", description="Quita una habilidad aprendible por nombre.")
    async def pj_habilidad_quitar(self, interaction: discord.Interaction, nombre_habilidad: str, nombre: Optional[str] = None):
        ch, cname, err = self.must_get_character(interaction.user.id, nombre)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        assert ch and cname

        skills = ch["kit_habilidades"].get("habilidades_aprendibles", [])
        new_list = [s for s in skills if not (isinstance(s, dict) and s.get("nombre") == nombre_habilidad)]
        if len(new_list) == len(skills):
            await interaction.response.send_message("No encontré esa habilidad.", ephemeral=True)
            return

        ch["kit_habilidades"]["habilidades_aprendibles"] = new_list
        self.update_character(interaction.user.id, cname, ch)
        await interaction.response.send_message(f"✅ Habilidad **{nombre_habilidad}** quitada.", ephemeral=True)

    # ---------------- STAFF (Slash) ----------------
    @staff.command(name="borrar", description="Borra un personaje (solo staff).")
    async def staff_borrar(self, interaction: discord.Interaction, user: discord.User, nombre_personaje: str):
        if not isinstance(interaction.user, discord.Member) or not _is_staff(interaction.user):
            await interaction.response.send_message("No tienes permisos de staff.", ephemeral=True)
            return

        data = _load_user(user.id)
        root = _get_user_root(data, user.id)

        if nombre_personaje not in root["personajes"]:
            await interaction.response.send_message("Ese personaje no existe.", ephemeral=True)
            return

        del root["personajes"][nombre_personaje]
        _save_user(user.id, data)
        await interaction.response.send_message(f"🗑️ Personaje **{nombre_personaje}** borrado para <@{user.id}>.", ephemeral=True)

    @staff.command(name="setnivel", description="Setea nivel del personaje (solo staff).")
    async def staff_setnivel(self, interaction: discord.Interaction, user: discord.User, nombre_personaje: str, nivel: int):
        if not isinstance(interaction.user, discord.Member) or not _is_staff(interaction.user):
            await interaction.response.send_message("No tienes permisos de staff.", ephemeral=True)
            return

        data = _load_user(user.id)
        ch = _get_character(data, user.id, nombre_personaje)
        if not ch:
            await interaction.response.send_message("Ese personaje no existe.", ephemeral=True)
            return

        old = int(ch.get("nivel", 1))
        new = max(1, int(nivel))
        ch["nivel"] = new
        if new > old:
            _apply_role_leveling(ch, old, new)

        _save_user(user.id, data)
        await interaction.response.send_message(f"✅ Nivel de **{nombre_personaje}** seteado a {ch['nivel']}.", ephemeral=True)

    @staff.command(name="addxp", description="Suma experiencia al personaje (solo staff).")
    async def staff_addxp(self, interaction: discord.Interaction, user: discord.User, nombre_personaje: str, xp: int):
        if not isinstance(interaction.user, discord.Member) or not _is_staff(interaction.user):
            await interaction.response.send_message("No tienes permisos de staff.", ephemeral=True)
            return

        data = _load_user(user.id)
        ch = _get_character(data, user.id, nombre_personaje)
        if not ch:
            await interaction.response.send_message("Ese personaje no existe.", ephemeral=True)
            return

        ch["experiencia"] = max(0, int(ch.get("experiencia", 0)) + int(xp))
        _save_user(user.id, data)
        await interaction.response.send_message(f"✅ XP de **{nombre_personaje}** ahora es {ch['experiencia']}.", ephemeral=True)

    @staff.command(name="crear_para", description="Crea un personaje para otro usuario (solo staff).")
    async def staff_crear_para(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        nombre: str,
        apodo: str,
        rol: str,
        profesion: str,
        nacion: str,
    ):
        if not isinstance(interaction.user, discord.Member) or not _is_staff(interaction.user):
            await interaction.response.send_message("No tienes permisos de staff.", ephemeral=True)
            return

        data = _load_user(user.id)
        root = _get_user_root(data, user.id)
        ok, msg = _can_create_more(root)
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # Validar duplicados
        if nombre in root["personajes"]:
            await interaction.response.send_message("Ya existe un personaje con ese nombre.", ephemeral=True)
            return

        for c in root["personajes"].values():
            if isinstance(c, dict) and c.get("apodo") == apodo:
                await interaction.response.send_message("El apodo ya está en uso por ese usuario.", ephemeral=True)
                return

        # Crear
        root["personajes"][nombre] = _new_character(nombre, apodo, rol, profesion, nacion)
        _save_user(user.id, data)

        await interaction.response.send_message(
            f"✅ Personaje **{nombre}** creado para <@{user.id}>.\n"
            f"Total actual: {len(root['personajes'])}/4",
            ephemeral=True
        )

    # ============================================================
    # PREFIX COMMANDS (=)
    # ============================================================
    @commands.group(name="pj", invoke_without_command=True)
    async def pj_prefix(self, ctx: commands.Context):
        await ctx.send(
            "📌 **Personajes**\n"
            "`=pj crear <Nombre> <Apodo>`\n"
            "`=pj ver basica [Nombre]`\n"
            "`=pj ver estadisticas [Nombre]`\n"
            "`=pj equipar_arma <JSON>`\n"
            "`=pj equipar_artefacto <slot> <JSON>` (slot: caliz/moneda/arma_artefacto/baston)\n"
            "`=pj quitar_artefacto <slot>` | `=pj quitar_arma`\n"
            "`=pj habilidad_agregar <nombre>|<descripcion>|<Activa/Pasiva>|<costo_tipo>|<costo_valor>|<stat>|<mult>`\n"
            "`=pj habilidad_quitar <nombre>`"
        )

    @pj_prefix.command(name="crear")
    async def pj_prefix_crear(self, ctx: commands.Context, nombre: str, apodo: str):
        data = _load_user(ctx.author.id)
        root = _get_user_root(data, ctx.author.id)
        if root["personajes"]:
            await ctx.send("Ya tienes un personaje. (Si quieres multi-personaje, lo habilitamos.)")
            return

        draft = CreateDraft(nombre=nombre, apodo=apodo)
        view = CreateTreeButtonsView(self, draft, "rol")
        await ctx.send(content="Selecciona tu **Rol**:", embed=view._embed(), view=view)

    @pj_prefix.command(name="ver")
    async def pj_prefix_ver(self, ctx: commands.Context, vista: str, nombre: Optional[str] = None):
        ch, cname, err = self.must_get_character(ctx.author.id, nombre)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        vista = vista.lower().strip()
        if vista == "basica":
            e = self.basic_embed(cname, ch)
        elif vista == "estadisticas":
            e = self.stats_embed(ch)
        else:
            await ctx.send("Vista inválida. Usa `basica` o `estadisticas`.")
            return

        await ctx.send(embed=e)

    @pj_prefix.command(name="equipar_artefacto")
    async def pj_prefix_equipar_artefacto(self, ctx: commands.Context, slot: str, *, item_json: str):
        slot = slot.lower().strip()
        if slot not in {"caliz", "moneda", "arma_artefacto", "baston"}:
            await ctx.send("Slot inválido. Usa: caliz/moneda/arma_artefacto/baston")
            return

        ch, cname, err = self.must_get_character(ctx.author.id, None)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        try:
            item = json.loads(item_json)
            if not isinstance(item, dict):
                raise ValueError
        except Exception:
            await ctx.send("El JSON del item no es válido.")
            return

        ch["equipamiento"]["artefactos"][slot] = item
        self.update_character(ctx.author.id, cname, ch)
        await ctx.send(f"✅ Artefacto equipado en **{slot}**.")

    @pj_prefix.command(name="quitar_artefacto")
    async def pj_prefix_quitar_artefacto(self, ctx: commands.Context, slot: str):
        slot = slot.lower().strip()
        if slot not in {"caliz", "moneda", "arma_artefacto", "baston"}:
            await ctx.send("Slot inválido. Usa: caliz/moneda/arma_artefacto/baston")
            return

        ch, cname, err = self.must_get_character(ctx.author.id, None)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        ch["equipamiento"]["artefactos"][slot] = None
        self.update_character(ctx.author.id, cname, ch)
        await ctx.send(f"✅ Quitado artefacto de **{slot}**.")

    @pj_prefix.command(name="equipar_arma")
    async def pj_prefix_equipar_arma(self, ctx: commands.Context, *, item_json: str):
        ch, cname, err = self.must_get_character(ctx.author.id, None)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        try:
            item = json.loads(item_json)
            if not isinstance(item, dict):
                raise ValueError
        except Exception:
            await ctx.send("El JSON del arma no es válido.")
            return

        ch["equipamiento"]["arma_principal"] = item
        self.update_character(ctx.author.id, cname, ch)
        await ctx.send("✅ Arma principal equipada.")

    @pj_prefix.command(name="quitar_arma")
    async def pj_prefix_quitar_arma(self, ctx: commands.Context):
        ch, cname, err = self.must_get_character(ctx.author.id, None)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        ch["equipamiento"]["arma_principal"] = None
        self.update_character(ctx.author.id, cname, ch)
        await ctx.send("✅ Arma principal quitada.")

    @pj_prefix.command(name="habilidad_agregar")
    async def pj_prefix_habilidad_agregar(self, ctx: commands.Context, *, payload: str):
        """
        Formato: nombre|descripcion|Activa/Pasiva|costo_tipo|costo_valor|stat|mult
        """
        parts = [p.strip() for p in payload.split("|")]
        if len(parts) != 7:
            await ctx.send("Formato inválido. Usa: nombre|descripcion|Activa/Pasiva|costo_tipo|costo_valor|stat|mult")
            return

        nombre_h, desc, tipo, costo_tipo, costo_valor, stat, mult = parts
        tipo = tipo.capitalize()
        if tipo not in {"Activa", "Pasiva"}:
            await ctx.send("Tipo inválido. Usa Activa o Pasiva.")
            return

        try:
            costo_valor_i = int(costo_valor)
            mult_f = float(mult)
        except Exception:
            await ctx.send("costo_valor debe ser int y mult debe ser float.")
            return

        ch, cname, err = self.must_get_character(ctx.author.id, None)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        skills = ch["kit_habilidades"].get("habilidades_aprendibles", [])
        if any(isinstance(s, dict) and s.get("nombre") == nombre_h for s in skills):
            await ctx.send("Ya tienes una habilidad con ese nombre.")
            return

        new_skill = {
            "nombre": nombre_h,
            "descripcion": desc,
            "tipo": tipo,
            "nivel_habilidad": 1,
            "costo": {"tipo": costo_tipo, "valor": costo_valor_i},
            "canalizacion_segundos": 0,
            "escalado": {"estadistica_base": stat, "multiplicador": mult_f},
            "bonificadores": {"bono_danio": 0.0, "bono_curacion": 0.0},
        }
        skills.append(new_skill)
        ch["kit_habilidades"]["habilidades_aprendibles"] = skills
        self.update_character(ctx.author.id, cname, ch)
        await ctx.send(f"✅ Habilidad **{nombre_h}** agregada.")

    @pj_prefix.command(name="habilidad_quitar")
    async def pj_prefix_habilidad_quitar(self, ctx: commands.Context, *, nombre_habilidad: str):
        ch, cname, err = self.must_get_character(ctx.author.id, None)
        if err:
            await ctx.send(err)
            return
        assert ch and cname

        skills = ch["kit_habilidades"].get("habilidades_aprendibles", [])
        new_list = [s for s in skills if not (isinstance(s, dict) and s.get("nombre") == nombre_habilidad)]
        if len(new_list) == len(skills):
            await ctx.send("No encontré esa habilidad.")
            return

        ch["kit_habilidades"]["habilidades_aprendibles"] = new_list
        self.update_character(ctx.author.id, cname, ch)
        await ctx.send(f"✅ Habilidad **{nombre_habilidad}** quitada.")

    # ---------------- STAFF PREFIX ----------------
    @commands.group(name="pjstaff", invoke_without_command=True)
    async def pjstaff_prefix(self, ctx: commands.Context):
        await ctx.send(
            "🛡️ **Staff**\n"
            "`=pjstaff borrar <@user> <NombrePersonaje>`\n"
            "`=pjstaff setnivel <@user> <NombrePersonaje> <Nivel>`\n"
            "`=pjstaff addxp <@user> <NombrePersonaje> <XP>`"
        )

    def _ctx_is_staff(self, ctx: commands.Context) -> bool:
        return isinstance(ctx.author, discord.Member) and _is_staff(ctx.author)

    @pjstaff_prefix.command(name="borrar")
    async def pjstaff_borrar(self, ctx: commands.Context, user: discord.User, nombre_personaje: str):
        if not self._ctx_is_staff(ctx):
            await ctx.send("No tienes permisos de staff.")
            return

        data = _load_user(user.id)
        root = _get_user_root(data, user.id)
        if nombre_personaje not in root["personajes"]:
            await ctx.send("Ese personaje no existe.")
            return

        del root["personajes"][nombre_personaje]
        _save_user(user.id, data)
        await ctx.send(f"🗑️ Personaje **{nombre_personaje}** borrado para <@{user.id}>.")

    @pjstaff_prefix.command(name="setnivel")
    async def pjstaff_setnivel(self, ctx: commands.Context, user: discord.User, nombre_personaje: str, nivel: int):
        if not self._ctx_is_staff(ctx):
            await ctx.send("No tienes permisos de staff.")
            return

        data = _load_user(user.id)
        ch = _get_character(data, user.id, nombre_personaje)
        if not ch:
            await ctx.send("Ese personaje no existe.")
            return

        old = int(ch.get("nivel", 1))
        new = max(1, int(nivel))
        ch["nivel"] = new
        if new > old:
            _apply_role_leveling(ch, old, new)

        _save_user(user.id, data)
        await ctx.send(f"✅ Nivel de **{nombre_personaje}** seteado a {ch['nivel']}.")

    @pjstaff_prefix.command(name="addxp")
    async def pjstaff_addxp(self, ctx: commands.Context, user: discord.User, nombre_personaje: str, xp: int):
        if not self._ctx_is_staff(ctx):
            await ctx.send("No tienes permisos de staff.")
            return

        data = _load_user(user.id)
        ch = _get_character(data, user.id, nombre_personaje)
        if not ch:
            await ctx.send("Ese personaje no existe.")
            return

        ch["experiencia"] = max(0, int(ch.get("experiencia", 0)) + int(xp))
        _save_user(user.id, data)
        await ctx.send(f"✅ XP de **{nombre_personaje}** ahora es {ch['experiencia']}.")
 
    @pjstaff_prefix.command(name="crear_para")
    async def pjstaff_crear_para(
        self,
        ctx: commands.Context,
        user: discord.User,
        nombre: str,
        apodo: str,
        rol: str,
        profesion: str,
        nacion: str,
    ):
        if not self._ctx_is_staff(ctx):
            await ctx.send("No tienes permisos de staff.")
            return

        data = _load_user(user.id)
        root = _get_user_root(data, user.id)

        ok, msg = _can_create_more(root)
        if not ok:
            await ctx.send(msg)
            return

        if nombre in root["personajes"]:
            await ctx.send("Ya existe un personaje con ese nombre.")
            return

        for c in root["personajes"].values():
            if isinstance(c, dict) and c.get("apodo") == apodo:
                await ctx.send("El apodo ya está en uso por ese usuario.")
                return

        root["personajes"][nombre] = _new_character(nombre, apodo, rol, profesion, nacion)
        _save_user(user.id, data)

        await ctx.send(
            f"✅ Personaje **{nombre}** creado para <@{user.id}> "
            f"({len(root['personajes'])}/4)."
        )


async def setup(bot: commands.Bot):
    print("✅ setup() de personaje.py ejecutado")
    await bot.add_cog(PersonajeCog(bot))

