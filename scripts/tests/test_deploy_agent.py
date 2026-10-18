"""Pruebas unitarias de deploy_agent.py con la API simulada (scripts/tests/fake_api.py).

Cubren: payload, idempotencia, validaciones locales y que la clave no se filtre.
NO prueban nada contra ElevenLabs real.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "tests"))

import deploy_agent as da  # noqa: E402
from elevenlabs_client import ApiError, ElevenLabsClient  # noqa: E402
from fake_api import FakeElevenLabs  # noqa: E402
from lint_files import lint_workflow  # noqa: E402

KEY = "xxxxx-test-key-SECRET"
BIG = "# Manual Haval H6 - tema\nFuente: Manual de usuario\n\n" + ("Texto del manual de prueba sobre un tema. " * 30)


def make_tree(tmp_path: Path, *, approve_resolutions: bool = True, files: dict[str, str] | None = None) -> Path:
    """Copia el prompt, la config y las resoluciones reales a un arbol temporal con manual sintetico."""
    root = tmp_path / "repo"
    (root / "agent_configs").mkdir(parents=True)
    for name in ("cdu-001-agent.json", "cdu-001-system-prompt.md", "cdu-001-prompt-resoluciones.json"):
        shutil.copy(REPO / "agent_configs" / name, root / "agent_configs" / name)
    if approve_resolutions:
        p = root / "agent_configs" / "cdu-001-prompt-resoluciones.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for r in data["resoluciones"]:
            r["aprobado"] = True
        p.write_text(json.dumps(data), encoding="utf-8")
    kdir = root / "knowledge" / "manual-h6"
    kdir.mkdir(parents=True)
    for fname, text in (files if files is not None else {"01-uno.md": BIG, "02-dos.md": BIG + " dos"}).items():
        (kdir / fname).write_text(text, encoding="utf-8")
    return root


def prepared(tmp_path, **kw):
    root = make_tree(tmp_path, **kw)
    cfg, prompt, docs = da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")
    return root, cfg, prompt, docs


def run_sync(fake, cfg, prompt, docs, **kw):
    client = ElevenLabsClient(fake.key, opener=fake, sleep=lambda s: None)
    ticks = iter(range(0, 10_000, 1))
    return da.sync(client, cfg, prompt, docs, sleep=lambda s: None, clock=lambda: float(next(ticks)), **kw)


# ------------------------------------------------------------------ prompt y marcadores
def test_prompt_real_tiene_marcadores_y_el_despliegue_falla():
    """Estado real del repo: el prompt v0.1 trae <...>; sin resoluciones aprobadas debe fallar claro."""
    with pytest.raises(da.DeployError) as exc:
        text = (REPO / "agent_configs" / "cdu-001-system-prompt.md").read_text(encoding="utf-8")
        prompt = da.extract_prompt_block(text)
        res = json.loads((REPO / "agent_configs" / "cdu-001-prompt-resoluciones.json").read_text(encoding="utf-8"))
        prompt, pending = da.apply_resolutions(prompt, res)
        da.check_unresolved(prompt, pending)
    msg = str(exc.value)
    assert "<del manual>" in msg and "sin resolver" in msg and "aprobado" in msg


def test_resoluciones_propuestas_aprobadas_limpian_todos_los_marcadores(tmp_path):
    _, _, prompt, _ = prepared(tmp_path)
    assert not da.MARKER_RE.search(prompt)
    assert "voseo" in prompt  # el resto del prompt aprobado queda intacto
    assert "Haval H6, edición 2021" in prompt


def test_sin_aprobar_falla(tmp_path):
    root = make_tree(tmp_path, approve_resolutions=False)
    with pytest.raises(da.DeployError, match="marcadores sin resolver"):
        da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")


def test_por_definir_tambien_bloquea():
    with pytest.raises(da.DeployError):
        da.check_unresolved("Hola [POR DEFINIR tono]", [])


def test_variables_dinamicas_propias_bloquean_pero_las_de_sistema_no():
    da.check_dynamic_variables("Tu numero es {{system__caller_id}}")
    with pytest.raises(da.DeployError, match="variables dinamicas"):
        da.check_dynamic_variables("Hola {{nombre}}")


def test_extraer_bloque_exige_encabezado_y_cerco():
    assert da.extract_prompt_block("## Prompt\n\n```\nhola\n```\n") == "hola"
    with pytest.raises(da.DeployError):
        da.extract_prompt_block("sin bloque")


# ----------------------------------------------------------------------------- manual
def test_sin_carpeta_de_manual(tmp_path):
    root = make_tree(tmp_path)
    shutil.rmtree(root / "knowledge")
    with pytest.raises(da.DeployError, match="No existe la carpeta knowledge/manual-h6"):
        da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")


def test_carpeta_vacia(tmp_path):
    root = make_tree(tmp_path, files={})
    with pytest.raises(da.DeployError, match="no tiene archivos .md"):
        da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")


def test_archivo_menor_a_500_bytes(tmp_path):
    root = make_tree(tmp_path, files={"01-ok.md": BIG, "02-chico.md": "x" * 499})
    with pytest.raises(da.DeployError, match=r"02-chico\.md \(499 bytes\)"):
        da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")


def test_exactamente_500_bytes_pasa(tmp_path):
    root = make_tree(tmp_path, files={"01-ok.md": "y" * 500})
    da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")


def test_total_mayor_a_2mb(tmp_path):
    chunk = "z" * 600_000
    root = make_tree(tmp_path, files={f"{i:02d}.md": chunk for i in range(4)})  # 2.4 MB
    with pytest.raises(da.DeployError, match="2 MB"):
        da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")


def test_se_ignoran_cobertura_y_readme(tmp_path):
    root = make_tree(tmp_path)
    (root / "knowledge" / "manual-h6" / "_cobertura.json").write_text("{}")
    (root / "knowledge" / "manual-h6" / "README.md").write_text("x" * 10)
    _, _, _, docs = prepared(tmp_path / "otro")
    assert [d.filename for d in docs] == ["01-uno.md", "02-dos.md"]
    cfg = da.load_config(root / "agent_configs" / "cdu-001-agent.json")
    assert [d.filename for d in da.load_knowledge(root, cfg["deploy"])] == ["01-uno.md", "02-dos.md"]


# ----------------------------------------------------------------------------- payload
def test_payload(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    kb = da.kb_locators(docs, {d.name: f"id_{i}" for i, d in enumerate(docs)})
    payload = da.build_payload(cfg, prompt, kb)
    ag = payload["conversation_config"]["agent"]
    assert ag["language"] == "es"
    assert ag["first_message"] == ""
    assert ag["prompt"]["prompt"] == prompt
    assert ag["prompt"]["rag"]["enabled"] is True
    assert ag["prompt"]["built_in_tools"]["end_call"]["params"] == {"system_tool_type": "end_call"}
    assert ag["prompt"]["knowledge_base"] == [
        {"type": "text", "name": docs[0].name, "id": "id_0", "usage_mode": "auto"},
        {"type": "text", "name": docs[1].name, "id": "id_1", "usage_mode": "auto"},
    ]
    assert "deploy" not in payload and "dynamic_variables" not in ag
    assert payload["name"] == "CDU-001 Haval H6 - manual (POC)"
    assert not any(k.startswith("_") for k in json.dumps(payload).split('"') if k.startswith("_"))


def test_config_no_puede_traer_prompt_ni_kb(tmp_path):
    root = make_tree(tmp_path)
    cfg = da.load_config(root / "agent_configs" / "cdu-001-agent.json")
    cfg["agent"]["conversation_config"]["agent"]["prompt"]["prompt"] = "x"
    with pytest.raises(da.DeployError, match="no debe traer"):
        da.check_agent_section(cfg["agent"])


@pytest.mark.parametrize(
    "mutate,msg",
    [
        (lambda a: a.update(language="en"), "language"),
        (lambda a: a.update(first_message="Hola"), "first_message"),
        (lambda a: a["prompt"]["rag"].update(enabled=False), "RAG"),
        (lambda a: a["prompt"]["built_in_tools"].pop("end_call"), "end_call"),
    ],
)
def test_reglas_de_configuracion(tmp_path, mutate, msg):
    root = make_tree(tmp_path)
    cfg = da.load_config(root / "agent_configs" / "cdu-001-agent.json")
    mutate(cfg["agent"]["conversation_config"]["agent"])
    with pytest.raises(da.DeployError, match=msg):
        da.check_agent_section(cfg["agent"])


# ------------------------------------------------------------------------- idempotencia
def test_primer_despliegue_crea_todo(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    rep = run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    assert rep.agent_action == "creado" and rep.agent_id.startswith("agent_")
    assert len(fake.docs) == 2 and len(fake.agents) == 1
    assert len(rep.docs_created) == 2 and rep.docs_skipped == []
    assert set(rep.index_status.values()) == {"succeeded"}
    stored = fake.agents[rep.agent_id]["conversation_config"]["agent"]["prompt"]
    assert {k["id"] for k in stored["knowledge_base"]} == set(fake.docs)


def test_segunda_corrida_no_duplica(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    first = run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    fake.calls.clear()
    second = run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    assert second.agent_id == first.agent_id and second.agent_action == "actualizado"
    assert len(fake.docs) == 2 and len(fake.agents) == 1
    assert second.docs_created == [] and len(second.docs_skipped) == 2
    assert ("POST", "/v1/convai/knowledge-base/text") not in fake.calls
    assert ("POST", "/v1/convai/agents/create") not in fake.calls


def test_contenido_cambiado_crea_nuevo_y_marca_obsoleto_y_prune_borra(tmp_path):
    root, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    (root / "knowledge" / "manual-h6" / "01-uno.md").write_text(BIG + " editado", encoding="utf-8")
    _, _, docs2 = da.prepare_local(root, root / "agent_configs" / "cdu-001-agent.json")
    rep = run_sync(fake, cfg, prompt, docs2, dry_run=False, prune=False)
    assert len(rep.docs_created) == 1 and len(rep.docs_stale) == 1
    assert len(fake.docs) == 3  # el obsoleto sigue ahi sin prune
    assert any("prune=true" in w for w in rep.warnings)
    rep2 = run_sync(fake, cfg, prompt, docs2, dry_run=False, prune=True)
    assert len(rep2.docs_deleted) == 1 and len(fake.docs) == 2
    assert all(d["name"] in {x.name for x in docs2} for d in fake.docs.values())


def test_dry_run_no_escribe(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    rep = run_sync(fake, cfg, prompt, docs, dry_run=True, prune=True)
    assert fake.writes() == []
    assert rep.agent_action == "crearia" and len(rep.docs_created) == 2
    assert fake.docs == {} and fake.agents == {}


def test_dry_run_con_agente_existente(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    fake.calls.clear()
    rep = run_sync(fake, cfg, prompt, docs, dry_run=True, prune=False)
    assert fake.writes() == [] and rep.agent_action == "actualizaria"
    assert set(rep.index_status.values()) == {"succeeded"}


def test_dos_agentes_con_el_mismo_nombre_falla(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    for _ in range(2):
        fake.agents[fake._next("agent_")] = {"name": cfg["agent"]["name"]}
    with pytest.raises(da.DeployError, match="agent_id"):
        run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)


def test_agent_id_fijado_y_validado(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    created = run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    rep = run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False, agent_id_override=created.agent_id)
    assert rep.agent_id == created.agent_id
    with pytest.raises(da.DeployError, match="formato"):
        run_sync(fake, cfg, prompt, docs, dry_run=True, prune=False, agent_id_override="../x; rm -rf")


def test_indice_fallido_detiene(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    fake.index_final_status = "rag_limit_exceeded"
    with pytest.raises(da.DeployError, match="rag_limit_exceeded"):
        run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    assert fake.agents == {}  # no se crea el agente si el indice fallo


def test_espera_de_indice_y_tiempo_agotado(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    fake = FakeElevenLabs(KEY)
    fake.index_polls_until_done = 2
    rep = run_sync(fake, cfg, prompt, docs, dry_run=False, prune=False)
    assert set(rep.index_status.values()) == {"succeeded"}
    fake2 = FakeElevenLabs(KEY)
    fake2.index_polls_until_done = 10**6
    cfg["deploy"]["index_wait_seconds"] = 3
    with pytest.raises(da.DeployError, match="Tiempo agotado"):
        run_sync(fake2, cfg, prompt, docs, dry_run=False, prune=False)


def test_lectura_de_vuelta_detecta_diferencias(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    payload = da.build_payload(cfg, prompt, da.kb_locators(docs, {d.name: d.name for d in docs}))
    remote = json.loads(json.dumps(payload))
    assert da.verify_agent(remote, payload, [d.name for d in docs]) == []
    remote["conversation_config"]["agent"]["prompt"]["prompt"] = "otro"
    remote["conversation_config"]["agent"]["prompt"]["rag"]["enabled"] = False
    diffs = da.verify_agent(remote, payload, [d.name for d in docs])
    assert any("prompt" in d for d in diffs) and any("RAG" in d for d in diffs)
    assert da.verify_agent({}, payload, [])[0].startswith("la respuesta de la API")


# ----------------------------------------------------------------------------- cliente
def test_reintenta_5xx_en_lecturas_pero_no_duplica_creaciones():
    fake = FakeElevenLabs(KEY)
    client = ElevenLabsClient(KEY, opener=fake, sleep=lambda s: None)
    fake.fail_next = [(503, "x"), (502, "x")]
    assert client.list_documents("p")  == []
    assert len(fake.calls) == 3
    fake.calls.clear()
    fake.fail_next = [(500, "boom")]
    with pytest.raises(ApiError):
        client.create_text_document("n", "t")
    assert len(fake.calls) == 1  # no se reintenta la creacion ante 500
    fake.calls.clear()
    fake.fail_next = [(429, "slow")]
    client.create_text_document("n", "t")
    assert len(fake.calls) == 2  # 429 si: el servidor no la proceso


def test_reintentos_acotados():
    fake = FakeElevenLabs(KEY)
    client = ElevenLabsClient(KEY, opener=fake, sleep=lambda s: None)
    fake.fail_next = [(503, "x")] * 10
    with pytest.raises(ApiError) as exc:
        client.list_agents("a")
    assert len(fake.calls) == 4 and exc.value.status == 503


def test_422_muestra_el_detalle():
    fake = FakeElevenLabs(KEY)
    client = ElevenLabsClient(KEY, opener=fake, sleep=lambda s: None)
    fake.fail_next = [(422, '{"detail":[{"loc":["body","conversation_config"],"msg":"llm invalido"}]}')]
    with pytest.raises(ApiError, match="llm invalido"):
        client.create_agent({})


def test_cabecera_con_clave_y_sin_clave_en_url():
    fake = FakeElevenLabs(KEY)
    client = ElevenLabsClient(KEY, opener=fake, sleep=lambda s: None)
    client.list_documents("p")
    assert fake.last_headers["xi-api-key"] == KEY


# ------------------------------------------------------------------- la clave no se filtra
def test_la_clave_no_aparece_en_errores_aunque_el_servidor_la_devuelva():
    fake = FakeElevenLabs(KEY)
    client = ElevenLabsClient(KEY, opener=fake, sleep=lambda s: None)
    fake.fail_next = [(401, f'{{"detail":"key {KEY} rechazada"}}')]
    with pytest.raises(ApiError) as exc:
        client.list_agents("a")
    assert KEY not in str(exc.value) and "***" in str(exc.value)


def test_main_sin_clave_falla_sin_red(tmp_path, monkeypatch, capsys):
    root = make_tree(tmp_path)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    def boom(_key):
        raise AssertionError("no debe crear cliente")

    code = da.main(["--dry-run", "--root", str(root), "--config", str(root / "agent_configs" / "cdu-001-agent.json")], boom)
    err = capsys.readouterr().err
    assert code == 1 and "ELEVENLABS_API_KEY" in err and "POC" in err


def test_main_check_no_necesita_clave_ni_red(tmp_path, monkeypatch, capsys):
    root = make_tree(tmp_path)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    code = da.main(["--check", "--root", str(root), "--config", str(root / "agent_configs" / "cdu-001-agent.json")])
    assert code == 0 and "no se uso la red" in capsys.readouterr().out


def test_main_completo_no_imprime_la_clave_ni_la_escribe_en_el_resumen(tmp_path, monkeypatch, capsys):
    root = make_tree(tmp_path)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("ELEVENLABS_API_KEY", KEY)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    fake = FakeElevenLabs(KEY)
    argv = ["--root", str(root), "--config", str(root / "agent_configs" / "cdu-001-agent.json")]
    code = da.main(argv, lambda k: ElevenLabsClient(k, opener=fake, sleep=lambda s: None))
    out = capsys.readouterr()
    assert code == 0
    assert KEY not in out.out + out.err
    text = summary.read_text(encoding="utf-8")
    assert KEY not in text
    assert "ID del agente" in text and "agent_" in text and "Estado del indice RAG" in text
    assert text.count("succeeded") == 2


def test_main_con_error_de_api_no_filtra_la_clave(tmp_path, monkeypatch, capsys):
    root = make_tree(tmp_path)
    monkeypatch.setenv("ELEVENLABS_API_KEY", KEY)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    fake = FakeElevenLabs(KEY)
    fake.fail_next = [(401, f"clave {KEY} invalida")]
    argv = ["--dry-run", "--root", str(root), "--config", str(root / "agent_configs" / "cdu-001-agent.json")]
    code = da.main(argv, lambda k: ElevenLabsClient(k, opener=fake, sleep=lambda s: None))
    out = capsys.readouterr()
    assert code == 1 and KEY not in out.out + out.err and "HTTP 401" in out.err


def test_excepcion_inesperada_no_vuelca_traza_ni_clave(tmp_path, monkeypatch, capsys):
    root = make_tree(tmp_path)
    monkeypatch.setenv("ELEVENLABS_API_KEY", KEY)

    def factory(k):
        raise RuntimeError(f"fallo con {k}")

    code = da.main(["--dry-run", "--root", str(root), "--config", str(root / "agent_configs" / "cdu-001-agent.json")], factory)
    out = capsys.readouterr()
    assert code == 1 and KEY not in out.out + out.err and "Traceback" not in out.err


def test_el_resumen_dry_run_lo_dice(tmp_path):
    _, cfg, prompt, docs = prepared(tmp_path)
    rep = run_sync(FakeElevenLabs(KEY), cfg, prompt, docs, dry_run=True, prune=False)
    assert "no se cambio nada" in da.render_summary(rep)


# ------------------------------------------------------------------------------ workflow
def test_workflow_real_cumple_invariantes():
    wf = REPO / ".github" / "workflows" / "deploy-agent.yml"
    assert lint_workflow(wf) == []
    import yaml

    doc = yaml.safe_load(wf.read_text(encoding="utf-8"))
    assert doc["jobs"]["deploy"]["environment"] == "POC"
    assert "environment" not in doc["jobs"]["validate"]
    assert "ELEVENLABS_API_KEY" not in json.dumps(doc["jobs"]["validate"])
    trig = doc.get("on", doc.get(True))
    assert trig["workflow_dispatch"]["inputs"]["dry_run"]["default"] is True
    assert trig["workflow_dispatch"]["inputs"]["prune"]["default"] is False
    assert doc["permissions"] == {"contents": "read"}


def test_lint_detecta_workflow_inseguro(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        "name: x\non: workflow_dispatch\npermissions:\n  contents: read\njobs:\n  j:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - uses: actions/checkout@main\n      - run: |\n          set -x\n"
        "          echo ${{ secrets.ELEVENLABS_API_KEY }}\n",
        encoding="utf-8",
    )
    errors = "\n".join(lint_workflow(bad))
    assert "environment: POC" in errors and "set -x" in errors and "fijada" in errors and "run:" in errors
