"""Pruebas del manual troceado (knowledge/manual-h6) y del script scripts/extract_manual.py.

Ejecutar:  python3 -m pytest scripts/tests -q

Las pruebas de artefactos leen lo ya generado en knowledge/manual-h6 y no necesitan el PDF.
Las de reproducibilidad (determinismo y --check) vuelven a ejecutar el script y SI necesitan
el PDF: se indica con la variable MANUAL_PDF (por defecto, la ruta usada en la sesion de
desarrollo). Si el PDF no esta, esas pruebas se OMITEN (skip) y el resumen lo muestra;
no cuentan como superadas.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "extract_manual.py"
OUT = REPO / "knowledge" / "manual-h6"
DEFAULT_PDF = "/mnt/user-data/uploads/Documents/poc-agents/manual-haval-h6_compressed.pdf"
PDF = os.environ.get("MANUAL_PDF", DEFAULT_PDF)

sys.path.insert(0, str(REPO / "scripts"))
import extract_manual as em  # noqa: E402

CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def docs():
    return sorted(p for p in OUT.glob("[0-9][0-9]-*.md"))


@pytest.fixture(scope="module")
def report():
    return json.loads((OUT / "_cobertura.json").read_text(encoding="utf-8"))


needs_pdf = pytest.mark.skipif(not Path(PDF).is_file(), reason=f"no hay PDF en {PDF} (defina MANUAL_PDF)")


# ----------------------------------------------------------------------------- cobertura


def test_hay_documentos():
    assert len(docs()) >= 20


def test_ninguna_pagina_con_texto_queda_sin_ubicar(report):
    r = report["resumen"]
    assert r["paginas_sin_ubicar"] == 0
    assert r["paginas_sin_ubicar_lista"] == []
    assert r["paginas_totales"] == len(report["paginas"]) == 299
    for p in report["paginas"]:
        if not p["sin_texto"]:
            assert p["documentos"], f"pagina {p['pdf']} con texto sin documento"


def test_paginas_sin_texto_son_las_medidas(report):
    # Paginas del PDF sin ningun contenido tras quitar numero de pagina y pestana.
    assert report["resumen"]["paginas_sin_texto_lista"] == [2, 3, 241, 285]
    assert report["resumen"]["paginas_con_texto"] + report["resumen"]["paginas_sin_texto"] == 299


def test_contabilidad_de_caracteres_pagina_por_pagina(report):
    # entrada = conservado + descartado  y  lo conservado esta completo en la salida
    for p in report["paginas"]:
        assert p["contabilidad_entrada_ok"], f"entrada no cuadra en la pagina {p['pdf']}"
        assert p["contenido_salida_completo"], f"salida incompleta en la pagina {p['pdf']}"
    assert report["resumen"]["problemas"] == []


def test_cobertura_coincide_con_los_archivos(report):
    on_disk = {p.name: p.stat().st_size for p in docs()}
    assert set(report["documentos"]) == set(on_disk)
    for name, info in report["documentos"].items():
        assert info["bytes"] == on_disk[name]
    assert report["resumen"]["bytes_md_total"] == sum(on_disk.values())
    # cada pagina apunta a documentos que existen
    for p in report["paginas"]:
        for d in p["documentos"]:
            assert d in on_disk


def test_desfase_de_paginas_medido(report):
    # pagina PDF = pagina impresa + 3 en las 296 paginas que tienen numero impreso
    assert report["resumen"]["desfase_pdf_menos_impresa"] == {"3": 296}


# ----------------------------------------------------------------------------- calidad de los .md


def test_ningun_md_menor_de_500_bytes():
    for p in docs():
        assert p.stat().st_size >= 500, p.name


def test_ningun_md_mayor_de_40kb():
    for p in docs():
        assert p.stat().st_size <= 40_000, p.name


def test_total_menor_de_2mb(report):
    total = sum(p.stat().st_size for p in docs())
    assert total < 2_000_000
    assert report["resumen"]["holgura_bytes"] == 2_000_000 - total


def test_sin_palabra_cortada_residual():
    bad = []
    for p in docs():
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"[a-záéíóúüñ]-(?: |\n)[a-záéíóúüñ]", text):
            bad.append((p.name, text[max(0, m.start() - 25):m.end() + 25]))
        for m in re.finditer(r"[a-záéíóúüñ]-$", text, re.M):
            bad.append((p.name, text[max(0, m.start() - 25):m.end() + 5]))
    assert not bad, bad[:5]


def test_sin_caracteres_chinos():
    for p in docs():
        text = p.read_text(encoding="utf-8")
        assert not CJK.search(text), p.name
        assert "书脊" not in text


def test_aviso_repetido_de_equipamiento_eliminado():
    # El aviso "Equipamiento del vehiculo ..." se repite 62 veces en el PDF; no debe quedar ninguno.
    for p in docs():
        text = p.read_text(encoding="utf-8")
        assert "Favor tenga en cuenta que este manual" not in text, p.name
        assert "Favor tenga en cuenta" not in text, p.name


def test_sin_codigos_de_figura_ni_numeros_sueltos_de_pagina():
    for p in docs():
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"\b[0-9A-F]{12}\b", text), f"{p.name}: codigo de figura"
        assert "〉" not in text and "【" not in text and "▷" not in text.replace("(▷Page X)", "")


def test_front_matter_en_todos_los_documentos():
    for p in docs():
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---\n"), p.name
        head = text.split("\n---\n", 1)[0]
        for key in ("titulo:", "capitulo:", "paginas_pdf:", "paginas_impresas:", "fuente:"):
            assert key in head, f"{p.name}: falta {key}"
        assert "ManualUsuarioHAVALH6" in head and "2021-12" in head


def test_avisos_conservan_la_palabra_al_inicio():
    for p in docs():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("> **"):
                assert re.match(r"> \*\*(Nota|Atención|Advertencia):\*\*", line), (p.name, line[:60])


def test_numero_de_avisos_igual_al_del_pdf():
    # El PDF tiene 141 'Nota', 100 'Atención' y 101 'Advertencia' (cuenta de etiquetas medida).
    text = "\n".join(p.read_text(encoding="utf-8") for p in docs())
    assert len(re.findall(r"^> \*\*Nota:\*\*", text, re.M)) == 141
    assert len(re.findall(r"^> \*\*Atención:\*\*", text, re.M)) == 100
    assert len(re.findall(r"^> \*\*Advertencia:\*\*", text, re.M)) == 101


def test_remisiones_de_pagina_validas():
    for p in docs():
        for n in re.findall(r"\(ver p\. (\d+)\)", p.read_text(encoding="utf-8")):
            assert 1 <= int(n) <= 296, (p.name, n)


def test_figura_no_incluida_una_vez_por_seccion():
    for p in docs():
        text = p.read_text(encoding="utf-8")
        for sec in re.split(r"^## ", text, flags=re.M)[1:]:
            assert sec.count("[figura no incluida]") <= 1, (p.name, sec.splitlines()[0])


def test_luces_del_tablero_presentes_por_nombre():
    text = (OUT / "02-conduccion-luces-indicadoras-de-los-instrumentos.md").read_text(encoding="utf-8")
    for name in ("Luz de advertencia de falla en las bolsas de aire",
                 "Luz de advertencia del sistema de monitoreo de presión de neumáticos",
                 "Luz de advertencia de falla del sistema de frenos",
                 "Luz de advertencia de la presión de aceite",
                 "Luz de advertencia de la temperatura del agua"):
        assert f"#### {name}" in text, name
    assert "[figura no incluida]" in text and "iconos" in text


# ----------------------------------------------------------------------------- tablas (valores del PDF)


@pytest.mark.parametrize("needle", [
    "Neumático estándar; Datos: 225/60 R18 100V / 225/55 R19 99V",
    "Rueda de repuesto; Datos: T135/90 R17 104M",
    "Modelo: GW4N20; Tipo: Motor turbocompresor de gasolina; Potencia neta máxima/Velocidad de rotación [KW/rpm]: 150/6000-6300",
    "Par neto máximo/Velocidad de rotación [N/rpm]: 320/1500-4000",
    "Modelo: GW4B15D; Tipo: Motor turbocompresor de gasolina; Potencia neta máxima/Velocidad de rotación [KW/rpm]: 110/5500-6000",
    "Modelo de motor: GW4N20; Volumen [L] (valor de referencia) › Al reemplazar el aceite y el filtro de aceite: 5,0±0,1",
    "Discos de freno delanteros › Límite mínimo de espesor [mm]; Datos: 26",
    "Ítem: Volumen del depósito [L] (valor de referencia); Datos: 61±1.8 (tracción en las dos ruedas) / 61±1.8 (tracción en las cuatro ruedas)",
    "Categoría de peso: Grupo I; Posiciones de asiento › Asiento del copiloto › Airbag del lado del copiloto está activado: X",
    "Alcance de detección [m]: 1,5",
])
def test_valores_de_tablas_coinciden_con_el_pdf(needle):
    text = "\n".join(p.read_text(encoding="utf-8") for p in docs())
    assert needle in text


def test_modelo_de_bateria_de_la_llave():
    text = "\n".join(p.read_text(encoding="utf-8") for p in docs())
    assert "Modelo de la batería: CR2032." in text


# ----------------------------------------------------------------------------- funciones del script


def test_union_de_guion_de_corte():
    assert em.join_line("la pági-", "na siguiente") == "la página siguiente"
    assert em.join_line("equi-", "pamientos") == "equipamientos"
    assert em.join_line("2021.12-", "X") == "2021.12- X"           # no es corte de palabra
    assert em.join_line("fin de frase.", "Otra") == "fin de frase. Otra"


def test_compuesto_con_guion_se_conserva():
    assert em.join_line("anti-", "niebla", {"anti-niebla"}) == "anti-niebla"


def test_normalizacion_de_texto():
    assert em.normalize_text("【configuración 】→【 interfaz】") == "[configuración]→[interfaz]"
    assert em.normalize_text("MP3、WMA") == "MP3, WMA"
    assert em.slugify("Recomendaciones para la conducción en el período de rodaje", 34) == "recomendaciones-para-la-conduccion"


# ----------------------------------------------------------------------------- reproducibilidad


@needs_pdf
def test_script_es_determinista(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for out in (a, b):
        subprocess.run([sys.executable, str(SCRIPT), PDF, "--out", str(out)], check=True,
                       capture_output=True, text=True)
    files_a = sorted(p.name for p in a.iterdir())
    assert files_a == sorted(p.name for p in b.iterdir())
    for name in files_a:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


@needs_pdf
def test_salida_versionada_coincide_con_el_script_y_check_pasa():
    r = subprocess.run([sys.executable, str(SCRIPT), PDF, "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--check: OK" in r.stdout


@needs_pdf
def test_check_detecta_cambios(tmp_path):
    out = tmp_path / "o"
    subprocess.run([sys.executable, str(SCRIPT), PDF, "--out", str(out)], check=True, capture_output=True)
    victim = next(out.glob("01-*.md"))
    victim.write_text(victim.read_text(encoding="utf-8") + "\nlinea manual extra\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), PDF, "--check", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "distinto en disco" in r.stdout
