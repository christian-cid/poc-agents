#!/usr/bin/env python3
"""Despliega el agente del CDU-001 en ElevenLabs por API REST (idempotente).

Modos:
  --check    Solo validaciones locales, SIN red y sin clave. Falla si el prompt tiene marcadores
             sin resolver, si falta el manual, si un .md pesa < 500 bytes o el total supera el tope.
  --dry-run  Valida y ademas hace lecturas (GET) contra ElevenLabs para mostrar que haria. No escribe.
  (sin flag) Sincroniza: crea los documentos que faltan, calcula el indice RAG, crea o actualiza el
             agente y verifica leyendo de vuelta.

Idempotencia (sin manifiesto en el repo): cada documento se llama
`<prefijo><archivo>__<sha256[:8]>`. Mismo nombre = mismo contenido = se omite. Si el contenido cambia
aparece un nombre nuevo y el anterior queda "obsoleto" (se borra solo con --prune). El agente se busca
por nombre exacto (o por --agent-id).

La clave se lee SOLO de ELEVENLABS_API_KEY y nunca se imprime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from elevenlabs_client import ApiError, ElevenLabsClient, key_from_env, redact  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "agent_configs" / "cdu-001-agent.json"
MARKER_RE = re.compile(r"<[^<>\n]{1,120}>")
POR_DEFINIR_RE = re.compile(r"\[POR DEFINIR[^\]]*\]", re.IGNORECASE)
DYN_VAR_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
AUTO_VARS_PREFIX = "system__"  # la plataforma rellena {{system__caller_id}} y {{system__called_number}}
MAX_STEM = 60  # acorta nombres largos; el limite de largo de nombre en la API no esta documentado
AGENT_ID_RE = re.compile(r"^agent_[A-Za-z0-9]+$")
FAILED_INDEX = {"failed", "rag_limit_exceeded", "document_too_small", "cannot_index_folder"}
PANEL_URL = "https://elevenlabs.io/app/agents/agents/{agent_id}"  # patron NO verificado en la documentacion


class DeployError(RuntimeError):
    """Error de validacion o de despliegue con mensaje claro para Christian."""


# --------------------------------------------------------------------------- modelo
@dataclass
class LocalDoc:
    filename: str
    size: int
    sha8: str
    name: str  # nombre remoto: prefijo + stem + __ + hash
    text: str


@dataclass
class Report:
    mode: str
    agent_name: str = ""
    agent_id: str = ""
    agent_action: str = ""
    prompt_sha8: str = ""
    docs_created: list[str] = field(default_factory=list)
    docs_skipped: list[str] = field(default_factory=list)
    docs_stale: list[dict[str, Any]] = field(default_factory=list)
    docs_deleted: list[str] = field(default_factory=list)
    index_status: dict[str, str] = field(default_factory=dict)
    rag_usage: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    total_bytes: int = 0


# ---------------------------------------------------------------------- configuracion
def load_config(path: Path) -> dict[str, Any]:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DeployError(f"No existe la configuracion del agente: {path}") from None
    except json.JSONDecodeError as exc:
        raise DeployError(f"JSON invalido en {path}: {exc}") from None
    for key in ("deploy", "agent"):
        if key not in cfg:
            raise DeployError(f"Falta la seccion '{key}' en {path}")
    return cfg


def extract_prompt_block(md_text: str, source: str = "el archivo del prompt") -> str:
    """Devuelve el contenido del primer bloque ``` que sigue al encabezado '## Prompt'."""
    m = re.search(r"^##\s+Prompt\s*\n+```[^\n]*\n(.*?)\n```", md_text, re.DOTALL | re.MULTILINE)
    if not m:
        raise DeployError(f"No encuentro el bloque ``` bajo el encabezado '## Prompt' en {source}.")
    block = m.group(1).strip("\n")
    if not block.strip():
        raise DeployError(f"El bloque del prompt en {source} esta vacio.")
    return block


def apply_resolutions(prompt: str, resolutions: dict[str, Any]) -> tuple[str, list[str]]:
    """Aplica solo resoluciones con aprobado=true. Devuelve (prompt, pendientes_de_aprobar)."""
    pending: list[str] = []
    for item in resolutions.get("resoluciones", []):
        buscar, reemplazar = item.get("buscar"), item.get("reemplazar")
        if not isinstance(buscar, str) or not isinstance(reemplazar, str) or not buscar:
            raise DeployError("Cada resolucion necesita 'buscar' y 'reemplazar' de tipo texto (y buscar no vacio).")
        if item.get("aprobado") is True:
            prompt = prompt.replace(buscar, reemplazar)
        elif buscar in prompt:
            pending.append(buscar)
    return prompt, pending


def check_unresolved(prompt: str, pending: list[str]) -> None:
    markers = sorted(set(MARKER_RE.findall(prompt)) | set(POR_DEFINIR_RE.findall(prompt)))
    if markers:
        lines = [
            "El prompt aun tiene marcadores sin resolver; el despliegue se detiene (nada se subio).",
            "Marcadores: " + ", ".join(markers),
        ]
        if pending:
            lines.append(
                "Hay resoluciones PROPUESTAS sin aprobar en agent_configs/cdu-001-prompt-resoluciones.json "
                "(aprobado=false). Quien decide (Christian) las aprueba poniendo aprobado=true, "
                "o se edita el prompt aprobado."
            )
        else:
            lines.append(
                "Resolvelos en agent_configs/cdu-001-system-prompt.md o agregá una resolucion aprobada en "
                "agent_configs/cdu-001-prompt-resoluciones.json."
            )
        raise DeployError("\n".join(lines))


def check_dynamic_variables(prompt: str) -> None:
    bad = sorted({v for v in DYN_VAR_RE.findall(prompt) if not v.startswith(AUTO_VARS_PREFIX)})
    if bad:
        raise DeployError(
            "El prompt usa variables dinamicas propias ({{" + "}}, {{".join(bad) + "}}). En WhatsApp una variable "
            "requerida sin valor hace fallar la conversacion; solo se permiten las que rellena la plataforma "
            f"({{{{{AUTO_VARS_PREFIX}...}}}})."
        )


def check_agent_section(agent: dict[str, Any]) -> None:
    """Reglas del CDU-001 sobre la configuracion (no inventa campos: solo exige lo decidido)."""
    try:
        ag = agent["conversation_config"]["agent"]
        pr = ag["prompt"]
    except KeyError as exc:
        raise DeployError(f"Falta {exc} en conversation_config.agent.prompt de la configuracion.") from None
    if "prompt" in pr or "knowledge_base" in pr:
        raise DeployError(
            "La configuracion no debe traer 'prompt' ni 'knowledge_base': se inyectan al desplegar "
            "(prompt desde su archivo, documentos desde knowledge/)."
        )
    if ag.get("language") != "es":
        raise DeployError("conversation_config.agent.language debe ser 'es' (decision del CDU-001).")
    if ag.get("first_message", "") != "":
        raise DeployError("first_message debe estar vacio: en WhatsApp inicia la persona.")
    if not pr.get("llm"):
        raise DeployError("Falta conversation_config.agent.prompt.llm.")
    rag = pr.get("rag") or {}
    if rag.get("enabled") is not True:
        raise DeployError("RAG debe estar activado (prompt.rag.enabled = true).")
    if not rag.get("embedding_model"):
        raise DeployError("Falta prompt.rag.embedding_model (el indice se calcula con ese modelo).")
    tool = (pr.get("built_in_tools") or {}).get("end_call")
    if not tool or (tool.get("params") or {}).get("system_tool_type") != "end_call":
        raise DeployError("Falta la herramienta de sistema end_call en prompt.built_in_tools.")


def strip_private(obj: Any) -> Any:
    """Quita claves que empiezan con '_' (comentarios del repo) antes de enviar a la API."""
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------- manual
def load_knowledge(root: Path, deploy_cfg: dict[str, Any]) -> list[LocalDoc]:
    kdir = root / deploy_cfg["knowledge_dir"]
    min_bytes = int(deploy_cfg["min_doc_bytes"])
    max_total = int(deploy_cfg["max_total_bytes"])
    prefix = deploy_cfg["doc_name_prefix"]
    rel = deploy_cfg["knowledge_dir"]
    if not kdir.is_dir():
        raise DeployError(
            f"No existe la carpeta {rel}/. El manual troceado todavia no esta en el repo "
            "(lo genera scripts/extract_manual.py). Sin manual no hay nada que desplegar."
        )
    files = sorted(
        p for p in kdir.glob("*.md") if not p.name.startswith("_") and p.name.upper() not in ("README.MD", "LEEME.MD")
    )
    if not files:
        raise DeployError(f"La carpeta {rel}/ no tiene archivos .md del manual.")
    docs: list[LocalDoc] = []
    small, undecodable = [], []
    for p in files:
        raw = p.read_bytes()
        if len(raw) < min_bytes:
            small.append(f"{p.name} ({len(raw)} bytes)")
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            undecodable.append(p.name)
            continue
        sha8 = hashlib.sha256(raw).hexdigest()[:8]
        docs.append(LocalDoc(p.name, len(raw), sha8, f"{prefix}{p.stem[:MAX_STEM]}__{sha8}", text))
    if small:
        raise DeployError(
            f"Archivos del manual por debajo de {min_bytes} bytes (ElevenLabs no los indexa con RAG): "
            + ", ".join(small)
            + ". Agrupalos con otros temas del mismo capitulo."
        )
    if undecodable:
        raise DeployError("Archivos que no son UTF-8 valido: " + ", ".join(undecodable))
    total = sum(d.size for d in docs)
    if total > max_total:
        raise DeployError(
            f"El manual pesa {total:,} bytes y el tope configurado es {max_total:,} (limite de indexado del "
            "plan Starter: 2 MB por workspace). Decidir entre recortar capitulos o subir de plan."
        )
    names = [d.name for d in docs]
    if len(set(names)) != len(names):
        raise DeployError("Dos archivos del manual producirian el mismo nombre de documento.")
    return docs


def build_payload(cfg: dict[str, Any], prompt: str, kb: list[dict[str, str]]) -> dict[str, Any]:
    """Cuerpo de crear/actualizar agente a partir de la configuracion del repo."""
    payload = strip_private(deepcopy(cfg["agent"]))
    pr = payload["conversation_config"]["agent"]["prompt"]
    pr["prompt"] = prompt
    pr["knowledge_base"] = kb
    return payload


def kb_locators(docs: list[LocalDoc], ids: dict[str, str]) -> list[dict[str, str]]:
    return [{"type": "text", "name": d.name, "id": ids[d.name], "usage_mode": "auto"} for d in docs]


def prepare_local(root: Path, config_path: Path) -> tuple[dict[str, Any], str, list[LocalDoc]]:
    """Todas las validaciones sin red. Devuelve (cfg, prompt_final, docs)."""
    cfg = load_config(config_path)
    d = cfg["deploy"]
    check_agent_section(cfg["agent"])
    prompt_path = root / d["prompt_file"]
    try:
        prompt = extract_prompt_block(prompt_path.read_text(encoding="utf-8"), d["prompt_file"])
    except FileNotFoundError:
        raise DeployError(f"No existe el archivo del prompt: {d['prompt_file']}") from None
    res_path = root / d["prompt_resolutions_file"]
    resolutions: dict[str, Any] = {}
    if res_path.exists():
        try:
            resolutions = json.loads(res_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DeployError(f"JSON invalido en {d['prompt_resolutions_file']}: {exc}") from None
    prompt, pending = apply_resolutions(prompt, resolutions)
    check_unresolved(prompt, pending)
    check_dynamic_variables(prompt)
    docs = load_knowledge(root, d)
    return cfg, prompt, docs


# ------------------------------------------------------------------------ sincronizacion
def wait_for_indexes(
    client: ElevenLabsClient,
    ids: dict[str, str],
    model: str,
    wait_seconds: int,
    poll_seconds: float,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> dict[str, str]:
    """Pide el indice (idempotente) y espera a que todos esten 'succeeded'."""
    status: dict[str, str] = {}
    for name, doc_id in ids.items():
        status[name] = str(client.compute_rag_index(doc_id, model).get("status", "desconocido"))
    deadline = clock() + wait_seconds
    while True:
        for name, st in status.items():
            if st in FAILED_INDEX:
                hint = {
                    "rag_limit_exceeded": " (se excedio el limite de indexado del plan: borra documentos obsoletos con prune o recorta el manual)",
                    "document_too_small": " (menos de 500 bytes)",
                }.get(st, "")
                raise DeployError(f"El indice RAG de '{name}' termino en estado '{st}'{hint}.")
        if all(st == "succeeded" for st in status.values()):
            return status
        if clock() >= deadline:
            pend = {n: s for n, s in status.items() if s != "succeeded"}
            raise DeployError(
                f"Tiempo agotado ({wait_seconds}s) esperando indices RAG. Pendientes: {pend}. "
                "Volve a correr el workflow: es idempotente y retoma donde quedo."
            )
        sleep(poll_seconds)
        for name, st in list(status.items()):
            if st == "succeeded":
                continue
            found = [i for i in client.get_rag_indexes(ids[name]) if i.get("model") == model]
            if found:
                status[name] = str(found[0].get("status", "desconocido"))


def find_agent(client: ElevenLabsClient, name: str, override: str | None) -> str | None:
    if override:
        if not AGENT_ID_RE.match(override):
            raise DeployError("agent_id con formato inesperado (se espera 'agent_...').")
        return override
    matches = [a for a in client.list_agents(name) if a.get("name") == name and not a.get("archived")]
    if len(matches) > 1:
        ids = ", ".join(str(a.get("agent_id")) for a in matches)
        raise DeployError(
            f"Hay {len(matches)} agentes llamados '{name}' ({ids}). Para no tocar el equivocado, "
            "corre el workflow con la entrada agent_id o archiva los sobrantes en el panel."
        )
    return str(matches[0]["agent_id"]) if matches else None


def verify_agent(remote: dict[str, Any], payload: dict[str, Any], expect_ids: list[str]) -> list[str]:
    """Lectura de vuelta: devuelve las diferencias encontradas (lista vacia = coincide)."""
    diffs: list[str] = []
    want = payload["conversation_config"]["agent"]
    try:
        got = remote["conversation_config"]["agent"]
        gp = got["prompt"]
    except (KeyError, TypeError):
        return ["la respuesta de la API no trae conversation_config.agent.prompt (esquema distinto al esperado)"]
    if got.get("language") != want["language"]:
        diffs.append(f"language: remoto={got.get('language')!r}")
    if (got.get("first_message") or "") != "":
        diffs.append("first_message no esta vacio en el remoto")
    if gp.get("prompt") != want["prompt"]["prompt"]:
        diffs.append("el prompt remoto no coincide con el del repo")
    if gp.get("llm") != want["prompt"]["llm"]:
        diffs.append(f"llm: remoto={gp.get('llm')!r}")
    if (gp.get("rag") or {}).get("enabled") is not True:
        diffs.append("RAG no quedo activado")
    if not ((gp.get("built_in_tools") or {}).get("end_call")):
        diffs.append("end_call no quedo configurado")
    remote_ids = {k.get("id") for k in gp.get("knowledge_base", [])}
    missing = [i for i in expect_ids if i not in remote_ids]
    if missing:
        diffs.append(f"{len(missing)} documento(s) no quedaron asociados al agente")
    return diffs


def sync(
    client: ElevenLabsClient,
    cfg: dict[str, Any],
    prompt: str,
    docs: list[LocalDoc],
    *,
    dry_run: bool,
    prune: bool,
    agent_id_override: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Report:
    d = cfg["deploy"]
    rag_model = cfg["agent"]["conversation_config"]["agent"]["prompt"]["rag"]["embedding_model"]
    rep = Report(mode="dry-run" if dry_run else "despliegue", agent_name=cfg["agent"]["name"])
    rep.prompt_sha8 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    rep.total_bytes = sum(x.size for x in docs)

    # 1) Documentos existentes con nuestro prefijo.
    remote = client.list_documents(d["doc_name_prefix"])
    by_name: dict[str, list[dict[str, Any]]] = {}
    for r in remote:
        by_name.setdefault(r["name"], []).append(r)
    ids: dict[str, str] = {}
    keep_ids: set[str] = set()
    for doc in docs:
        existing = sorted(by_name.get(doc.name, []), key=lambda r: str(r.get("id")))
        if existing:
            ids[doc.name] = existing[0]["id"]
            keep_ids.add(existing[0]["id"])
            rep.docs_skipped.append(doc.name)
    # 2) Crear los que faltan.
    for doc in docs:
        if doc.name in ids:
            continue
        if dry_run:
            rep.docs_created.append(doc.name + " (se crearia)")
            continue
        created = client.create_text_document(doc.name, doc.text)
        ids[doc.name] = created["id"]
        keep_ids.add(created["id"])
        rep.docs_created.append(doc.name)
    # 3) Documentos obsoletos (otro hash, duplicados) = con prefijo y fuera del conjunto deseado.
    for r in remote:
        if r["id"] not in keep_ids:
            size = (r.get("metadata") or {}).get("size_bytes")
            rep.docs_stale.append({"id": r["id"], "name": r["name"], "size_bytes": size})

    # 4) Indices RAG.
    if dry_run:
        for doc in docs:
            if doc.name not in ids:
                rep.index_status[doc.name] = "pendiente (documento nuevo)"
                continue
            found = [i for i in client.get_rag_indexes(ids[doc.name]) if i.get("model") == rag_model]
            rep.index_status[doc.name] = str(found[0].get("status")) if found else "sin calcular"
    else:
        rep.index_status = wait_for_indexes(
            client, ids, rag_model, int(d["index_wait_seconds"]), float(d["index_poll_seconds"]), sleep, clock
        )
    try:
        rep.rag_usage = client.get_rag_usage()
    except ApiError as exc:
        rep.warnings.append(f"No pude leer el uso del indice RAG del workspace: {exc}")

    # 5) Agente.
    agent_id = find_agent(client, cfg["agent"]["name"], agent_id_override)
    kb = kb_locators(docs, {n: ids.get(n, "ID_PENDIENTE") for n in (x.name for x in docs)})
    payload = build_payload(cfg, prompt, kb)
    if dry_run:
        rep.agent_id = agent_id or "(se crearia)"
        rep.agent_action = "actualizaria" if agent_id else "crearia"
    else:
        if agent_id:
            client.update_agent(agent_id, payload)
            rep.agent_action = "actualizado"
        else:
            agent_id = client.create_agent(payload)["agent_id"]
            rep.agent_action = "creado"
        rep.agent_id = agent_id
        diffs = verify_agent(client.get_agent(agent_id), payload, [ids[x.name] for x in docs])
        if diffs:
            raise DeployError(
                "El agente se escribio pero la lectura de vuelta no coincide: " + "; ".join(diffs)
                + ". Revisa el agente en el panel y manda este mensaje."
            )

    # 6) Limpieza (solo con --prune, y nunca en dry-run).
    if rep.docs_stale and prune and not dry_run:
        for s in rep.docs_stale:
            try:
                client.delete_document(s["id"], force=False)
                rep.docs_deleted.append(s["name"])
            except ApiError as exc:
                rep.warnings.append(f"No pude borrar '{s['name']}': {exc}")
    elif rep.docs_stale and not prune:
        total = sum(s["size_bytes"] or 0 for s in rep.docs_stale)
        rep.warnings.append(
            f"{len(rep.docs_stale)} documento(s) obsoleto(s) siguen en el workspace ({total:,} bytes) y cuentan para "
            "el limite de 2 MB de Starter. Corre el workflow con prune=true para borrarlos."
        )
    return rep


# ---------------------------------------------------------------------------- salida
def render_summary(rep: Report) -> str:
    ok = rep.mode == "despliegue"
    lines = [f"## Despliegue del agente CDU-001 ({rep.mode})", ""]
    if not ok:
        lines += ["> Modo dry-run: solo se hicieron lecturas; **no se cambio nada** en ElevenLabs.", ""]
    link = PANEL_URL.format(agent_id=rep.agent_id) if rep.agent_id.startswith("agent_") else "(aun no existe)"
    lines += [
        f"- **Agente:** {rep.agent_name}",
        f"- **ID del agente:** `{rep.agent_id}` ({rep.agent_action})",
        f"- **Enlace al panel:** {link} _(patron de URL no verificado: si no abre, entra a Agents y busca por nombre)_",
        f"- **Huella del prompt (sha256, 8 car.):** `{rep.prompt_sha8}`",
        f"- **Manual local:** {len(rep.docs_skipped) + len(rep.docs_created)} archivos, {rep.total_bytes:,} bytes",
        f"- **Documentos creados:** {len(rep.docs_created)} · **omitidos (ya estaban):** {len(rep.docs_skipped)} · "
        f"**obsoletos:** {len(rep.docs_stale)} · **borrados:** {len(rep.docs_deleted)}",
    ]
    if rep.rag_usage:
        lines.append(
            f"- **Uso de indice RAG del workspace:** {rep.rag_usage.get('total_used_bytes')} de "
            f"{rep.rag_usage.get('total_max_bytes')} bytes _(tal como lo reporta la API; el limite de Starter se mide sobre el tamano original)_"
        )
    lines += ["", "### Estado del indice RAG por documento", "", "| Documento | Estado |", "| --- | --- |"]
    for name, st in rep.index_status.items():
        lines.append(f"| `{name}` | {st} |")
    if rep.docs_created:
        lines += ["", "### Documentos creados", *[f"- `{n}`" for n in rep.docs_created]]
    if rep.docs_stale:
        lines += ["", "### Documentos obsoletos", *[f"- `{s['name']}` ({s['size_bytes']} bytes)" for s in rep.docs_stale]]
    if rep.warnings:
        lines += ["", "### Avisos", *[f"- {w}" for w in rep.warnings]]
    lines += [
        "",
        "Siguiente paso: abrir el agente en el panel de ElevenLabs y probarlo en el simulador. "
        "Nada de esto se ha probado todavia contra WhatsApp.",
    ]
    return "\n".join(lines) + "\n"


def write_summary(text: str, key: str | None) -> None:
    text = redact(text, key)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="solo validaciones locales, sin red ni clave")
    p.add_argument("--dry-run", action="store_true", help="lecturas contra ElevenLabs, sin escribir nada")
    p.add_argument("--prune", action="store_true", help="borra documentos obsoletos del prefijo del CDU-001")
    p.add_argument("--agent-id", default="", help="fija el agente a actualizar (agent_...) en vez de buscar por nombre")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.check and args.dry_run:
        p.error("--check y --dry-run son excluyentes")
    return args


def main(argv: list[str] | None = None, client_factory: Callable[[str], ElevenLabsClient] | None = None) -> int:
    args = parse_args(argv)
    key: str | None = None
    try:
        root = Path(args.root)
        cfg, prompt, docs = prepare_local(root, Path(args.config))
        total = sum(x.size for x in docs)
        print(f"Validacion local OK: prompt {len(prompt)} caracteres, {len(docs)} archivos del manual, {total:,} bytes.")
        if args.check:
            print("Modo --check: no se uso la red.")
            return 0
        key = key_from_env()
        client = client_factory(key) if client_factory else ElevenLabsClient(key)
        rep = sync(
            client, cfg, prompt, docs, dry_run=args.dry_run, prune=args.prune, agent_id_override=args.agent_id or None
        )
        write_summary(render_summary(rep), key)
        return 0
    except (DeployError, ApiError) as exc:
        print(f"ERROR: {redact(str(exc), key)}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - nunca volcar trazas que puedan contener secretos
        print(f"ERROR inesperado ({type(exc).__name__}): {redact(str(exc), key)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
