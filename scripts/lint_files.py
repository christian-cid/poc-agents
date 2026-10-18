#!/usr/bin/env python3
"""Lint sin red: sintaxis de YAML/JSON e invariantes de seguridad de los workflows.

Reglas de los workflows (constitucion, principio IV):
- Todo job que use ELEVENLABS_API_KEY declara `environment: POC`.
- La clave solo se referencia como `secrets.ELEVENLABS_API_KEY` dentro de un `env:` (nunca en `run:`).
- Ningun `run:` usa `set -x`, `echo` de la clave ni `--api-key`.
- Las acciones `uses:` estan fijadas a una version (tag completo) o SHA, no a una rama.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SECRET_REF = re.compile(r"secrets\.ELEVENLABS_API_KEY")
PINNED = re.compile(r"@(v?\d+(\.\d+){1,2}|[0-9a-f]{40})$")


def lint_workflow(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}: YAML invalido: {exc}"]
    if not isinstance(doc, dict) or "jobs" not in doc:
        return [f"{path}: no tiene `jobs`"]
    for name, job in doc["jobs"].items():
        steps = job.get("steps", [])
        job_dump = yaml.safe_dump(job)
        uses_secret = bool(SECRET_REF.search(job_dump))
        if uses_secret and job.get("environment") != "POC":
            errors.append(f"{path}: el job '{name}' usa ELEVENLABS_API_KEY sin `environment: POC`")
        if "ELEVENLABS_API_KEY" in str(job.get("env", {})) and "secrets." in str(job.get("env", {})):
            errors.append(f"{path}: el job '{name}' expone el secreto a TODOS los pasos; ponelo solo en el paso que lo necesita")
        for i, step in enumerate(steps):
            run = step.get("run", "") or ""
            if re.search(r"(^|\s)set\s+-[a-z]*x", run):
                errors.append(f"{path}: job '{name}' paso {i}: usa `set -x`")
            if SECRET_REF.search(run) or re.search(r"echo[^\n]*ELEVENLABS_API_KEY", run):
                errors.append(f"{path}: job '{name}' paso {i}: el secreto aparece dentro de `run:`")
            if "--api-key" in run:
                errors.append(f"{path}: job '{name}' paso {i}: la clave no puede ir como argumento")
            uses = step.get("uses")
            if uses and not uses.startswith("./") and not PINNED.search(uses):
                errors.append(f"{path}: job '{name}' paso {i}: `{uses}` no esta fijada a version o SHA")
    perms = doc.get("permissions")
    if perms is None:
        errors.append(f"{path}: falta `permissions:` a nivel de workflow (permisos minimos)")
    return errors


def lint_json(path: Path) -> list[str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: JSON invalido: {exc}"]
    return []


def main() -> int:
    errors: list[str] = []
    checked = 0
    for p in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        errors += lint_workflow(p)
        checked += 1
    for p in sorted((ROOT / "agent_configs").glob("*.json")):
        errors += lint_json(p)
        checked += 1
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    print(f"Lint: {checked} archivos revisados, {len(errors)} errores.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
