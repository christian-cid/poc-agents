#!/usr/bin/env python3
"""Extrae, limpia y trocea el manual del Haval H6 en markdown listo para indexar (RAG).

Uso:
    python3 scripts/extract_manual.py RUTA/AL/manual.pdf            # genera knowledge/manual-h6/
    python3 scripts/extract_manual.py RUTA/AL/manual.pdf --check    # solo verifica (no escribe)

Solo usa la biblioteca estandar de Python y las herramientas poppler (pdftotext,
pdftohtml, pdftocairo). El PDF tiene texto seleccionable: no se necesita OCR.

Datos de cada pagina (todos del mismo PDF):
  * pdftotext -raw  -> caracteres de entrada (medida oficial de cobertura).
  * pdftohtml -xml  -> lineas con posicion, tamano, color, negrita y enlaces. Se verifica
                       que contiene exactamente los mismos caracteres que pdftotext -raw.
  * pdftocairo -svg -> reglas (bordes de tablas y cierre de los recuadros de aviso).

La limpieza es conservadora y medible: cada item de texto del PDF se conserva o se
descarta bajo una categoria registrada, y por pagina se comprueba que
    caracteres de entrada = conservados + descartados      (contabilidad de entrada)
    contenido conservado == contenido escrito en los .md    (contabilidad de salida)
El resultado queda en _cobertura.json. Determinista: misma entrada, mismos bytes.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import hashlib
import html
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------- constantes

SOURCE_NAME = "ManualUsuarioHAVALH6"
SOURCE_EDITION = "2021-12"
MODEL = "GWM Haval H6"
MIN_BYTES = 500            # minimo por documento (plan Starter)
SOFT_MIN = 5_000           # tamano objetivo minimo (se fusionan secciones contiguas)
FUSE_TO = 8_000            # se sigue fusionando secciones contiguas hasta llegar a esto
MAX_DOC_BYTES = 40_000     # tamano objetivo maximo por documento
LIMIT_BYTES = 2_000_000    # 2 MB del plan Starter (se mide sobre el tamano del archivo subido)
SCALE = 1.5                # pdftohtml usa 1.5 px por punto
OFFSET_DEFAULT = 3         # pagina PDF - pagina impresa (se verifica contra los pies de pagina)

CIRC = "".join(chr(c) for c in range(0x24B6, 0x24D0))  # circulos Ⓐ..Ⓩ
CJK = re.compile(r"[一-鿿㐀-䶿]")
FIG_CODE = re.compile(r"^[0-9A-F]{12}$")
LEADER = re.compile(r"\.{4,}")
REF_END = re.compile(r"(\(ver p\. \d+\)|— p\. \d+)$")
LABELS = ("Nota", "Atención", "Advertencia")
BLUE = "#133f7b"
WHITE = "#ffffff"
LETTER = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
HYPH_WORD = re.compile(rf"[{LETTER}0-9]+(?:-[{LETTER}0-9]+)+")
SENT_END = (".", ":", ";", "!", "?", ")", "”", '"', "]")
CHAPTERS = {1: "Operación", 2: "Conducción", 3: "Sistema audiovisual", 4: "Seguridad",
            5: "Situaciones de Emergencia", 6: "Mantenimiento", 7: "Datos Técnicos", 8: "Índice"}
LIGHT_SECTION = re.compile(r"luces indicadoras de los instrumentos", re.I)
LIGHT_NOTE = ("*Nota del equipo: los iconos de las luces del tablero son imágenes del manual que no están "
              "en este texto. Cada luz aparece aquí con su nombre y su significado, tal como los dice el manual.*")

# Aviso que el manual repite al inicio de cada seccion (forma normalizada: solo letras).
NOTICE_START = "favortengaencuentaqueestemanualincluyetodoslosequipamientos"
NOTICE_END = "adquiridoelvehiculo"
NOTICE_HEADING = "equipamientodelvehiculo"
# Categorias de descarte que en realidad se conservan como titulo.
AS_TITLE = ("titulo_de_banda", "numero_de_capitulo_apertura")


def norm_letters(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


STOP = {"de", "del", "la", "las", "el", "los", "y", "a", "en", "al", "con", "por", "para"}
CHAPTER_SLUG = {1: "operacion", 2: "conduccion", 3: "audiovisual", 4: "seguridad", 5: "emergencia",
                6: "mantenimiento", 7: "datos-tecnicos", 8: "indice"}


def slugify(s: str, limit: int = 40) -> str:
    """Slug ascii que se corta en limite de palabra y no termina en una palabra vacia."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", s).split()]
    out = []
    for w in words:
        if len("-".join(out + [w])) > limit:
            break
        out.append(w)
    while len(out) > 1 and out[-1] in STOP:
        out.pop()
    return "-".join(out)


def nonspace(s: str) -> int:
    return len(re.sub(r"\s", "", s))


def alnum_counter(s: str) -> collections.Counter:
    return collections.Counter(c for c in s if c.isalnum())


def ranges(nums: list[int]) -> str:
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ", ".join(out)


# --------------------------------------------------------------------------- poppler


def run(cmd: list[str]) -> bytes:
    return subprocess.run(cmd, capture_output=True, check=True).stdout


class It:
    """Un fragmento de texto del PDF con su posicion y estilo."""
    __slots__ = ("page", "top", "left", "w", "h", "size", "color", "bold", "text", "href",
                 "cat", "fig", "blue_num", "orig")

    def __init__(self, page, top, left, w, h, size, color, bold, text, href):
        self.page, self.top, self.left, self.w, self.h = page, top, left, w, h
        self.size, self.color, self.bold, self.text, self.href = size, color, bold, text, href
        self.cat = None        # categoria de descarte (None = contenido)
        self.fig = False
        self.blue_num = False
        self.orig = None       # item original si este es un trozo de un item partido por una regla

    @property
    def cx(self):
        return self.left + self.w / 2

    @property
    def cy(self):
        return self.top + self.h / 2


def load_pages(pdf: str):
    raw_all = run(["pdftotext", "-raw", pdf, "-"]).decode("utf-8")
    raw_pages = raw_all.split("\f")
    if raw_pages and raw_pages[-1] == "":
        raw_pages.pop()
    xml = run(["pdftohtml", "-xml", "-i", "-stdout", pdf]).decode("utf-8")
    fonts = {i: (int(s), f, c) for i, s, f, c in re.findall(
        r'<fontspec id="(\d+)" size="(\d+)" family="([^"]+)" color="([^"]+)"', xml)}
    items: dict[int, list[It]] = {}
    for pm in re.finditer(r'<page number="(\d+)"[^>]*>(.*?)</page>', xml, re.S):
        n = int(pm.group(1))
        lst = []
        for m in re.finditer(r'<text top="(-?\d+)" left="(-?\d+)" width="(-?\d+)" height="(-?\d+)" '
                             r'font="(\d+)">(.*?)</text>', pm.group(2), re.S):
            raw = m.group(6)
            hm = re.search(r'href="[^"#]*#(\d+)"', raw)
            size, _fam, color = fonts[m.group(5)]
            text = html.unescape(re.sub(r"</?[a-zA-Z][^>]*>", "", raw))
            lst.append(It(n, int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)),
                          size, color, "<b>" in raw, text, int(hm.group(1)) if hm else None))
        items[n] = lst
    for n in range(1, len(raw_pages) + 1):
        items.setdefault(n, [])
    return len(raw_pages), raw_pages, items


def load_rules(pdf: str, n: int):
    """Segmentos de regla de la pagina en pixeles de pdftohtml.

    Devuelve (horizontales, verticales): (y, x1, x2, ancho) y (x, y1, y2, ancho). Solo trazos
    finos dentro del area de contenido (se descartan marcas de corte e iconos).
    """
    svg = run(["pdftocairo", "-svg", "-f", str(n), "-l", str(n), pdf, "-"]).decode("utf-8", "replace")
    hs, vs = [], []
    for m in re.finditer(r'<path fill="none" stroke-width="([\d.]+)"[^>]*stroke="[^"]+"[^>]*'
                         r'd="([^"]+)"(?: transform="matrix\(([^)]+)\))?', svg):
        w = float(m.group(1))
        if w > 0.6:
            continue
        a, b, c, d, e, f = [float(x) for x in m.group(3).split(",")] if m.group(3) else (1, 0, 0, 1, 0, 0)
        nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", m.group(2))]
        pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            X1, Y1 = (a * x1 + c * y1 + e) * SCALE, (b * x1 + d * y1 + f) * SCALE
            X2, Y2 = (a * x2 + c * y2 + e) * SCALE, (b * x2 + d * y2 + f) * SCALE
            if not (88 <= min(X1, X2) and max(X1, X2) <= 635 and 100 <= min(Y1, Y2) and max(Y1, Y2) <= 885):
                continue
            if abs(Y1 - Y2) < 0.7 and abs(X1 - X2) > 6:
                hs.append((round((Y1 + Y2) / 2, 1), round(min(X1, X2), 1), round(max(X1, X2), 1), w))
            elif abs(X1 - X2) < 0.7 and abs(Y1 - Y2) > 6:
                vs.append((round((X1 + X2) / 2, 1), round(min(Y1, Y2), 1), round(max(Y1, Y2), 1), w))
    return hs, vs


# --------------------------------------------------------------------------- pagina


class PageInfo:
    def __init__(self, n):
        self.n = n
        self.band = ""             # titulo de la banda superior (inicio de seccion)
        self.opener = False        # pagina de apertura de capitulo
        self.chapter_digit = None  # digito de la pestana lateral
        self.printed = None        # numero impreso (pie de pagina)
        self.sec = None            # indice de seccion
        self.kind = "contenido"    # contenido | toc | portada
        self.leaders = False       # la pagina tiene lineas con puntos guia (indice)
        self.tables = 0
        self.figures = 0
        self.dropped = collections.Counter()    # categoria -> caracteres sin espacios
        self.kept_src = 0                       # caracteres sin espacios conservados
        self.kept_norm = collections.Counter()  # alnum esperado en la salida
        self.out = collections.Counter()        # alnum escrito (sin duplicados de tabla)
        self.chars_out = 0
        self.chars_out_nospace = 0
        self.docs: list[str] = []
        self.rules_callout: list = []

    @property
    def printed_eff(self):
        if self.printed is not None:
            return self.printed
        return self.n - OFFSET_DEFAULT if self.n > OFFSET_DEFAULT else None


def classify_items(info: PageInfo, items: list[It]):
    """Marca mobiliario de pagina (pie, pestana, banda, codigos de figura, texto chino...)."""
    n = info.n
    for it in items:
        s = it.text.strip()
        if not s:
            it.cat = "espacio"
        elif CJK.search(s):
            it.cat = "texto_chino"
        elif it.size == 11 and it.top > 850:
            it.cat = "numero_de_pagina"
            if s.isdigit():
                info.printed = int(s)
        elif (it.left < 90 or it.left > 630) and it.top > 150:
            it.cat = "pestana_de_capitulo"
            if it.size == 19 and s.isdigit():
                info.chapter_digit = int(s)
        elif it.size == 8 and FIG_CODE.match(s):
            it.cat = "codigo_de_figura"
            it.fig = True
        elif it.size in (21, 39) and it.color == WHITE and it.top < 300:
            it.cat = "titulo_de_banda"
        elif it.size == 68 and it.bold:
            it.cat = "numero_de_capitulo_apertura"
            if s.isdigit():
                info.chapter_digit = int(s)
    bands = [i for i in items if i.cat == "titulo_de_banda"]
    if bands:
        info.band = join_texts([b.text.strip() for b in sorted(bands, key=lambda b: (b.top, b.left))])
        info.opener = any(b.size == 39 for b in bands)
    info.leaders = any(i.cat is None and LEADER.search(i.text) for i in items)


# --------------------------------------------------------------------------- texto


def join_texts(parts: list[str], vocab: set | None = None) -> str:
    out = ""
    for p in parts:
        out = join_line(out, p, vocab) if out else p
    return out


def join_line(a: str, b: str, vocab: set | None = None, stats: collections.Counter | None = None) -> str:
    """Une dos lineas consecutivas de un parrafo resolviendo el guion de corte de palabra."""
    if not a:
        return b
    if not b:
        return a
    m = re.search(rf"([{LETTER}]+)-$", a)
    n = re.match(rf"([{LETTER}]+)", b)
    if m and n:
        if b[0].islower():
            if vocab is not None and (m.group(1) + "-" + n.group(1)).lower() in vocab:
                if stats is not None:
                    stats["guion_conservado_compuesto"] += 1
                return a + b
            if stats is not None:
                stats["guion_de_corte_unido"] += 1
            return a[:-1] + b
        if stats is not None:
            stats["guion_conservado_siguiente_mayuscula"] += 1
        return a + b
    return a + " " + b


def normalize_text(s: str) -> str:
    s = s.replace(" ", " ").replace("​", "")
    s = s.replace("【", "[").replace("】", "]").replace("（", "(").replace("）", ")")
    s = s.replace("〉", "").replace("、", ", ").replace("：", ":").replace("，", ",")
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\[\s+", "[", re.sub(r"\s+\]", "]", s))


class Line:
    """Una linea visual (items con la misma altura)."""

    def __init__(self, it: It):
        self.items = [it]
        self.text = ""
        self.kind = "text"
        self.order = 0

    def add(self, it: It):
        self.items.append(it)

    @property
    def page(self):
        return self.items[0].page

    @property
    def text_items(self):
        return [i for i in self.items if i.text.strip() != "〉"]

    @property
    def top(self):
        ti = self.text_items or self.items
        return min(i.top for i in ti)

    @property
    def left(self):
        ti = self.text_items or self.items
        return min(i.left for i in ti)

    @property
    def col(self):
        return 1 if self.left >= 350 else 0

    @property
    def has_bullet(self):
        return any(i.text.strip() == "〉" for i in self.items)

    @property
    def size(self):
        return (self.text_items or self.items)[0].size

    @property
    def color(self):
        return (self.text_items or self.items)[0].color

    @property
    def all_bold(self):
        return bool(self.text_items) and all(i.bold for i in self.text_items)

    def build(self) -> str:
        """Compone el texto; remisiones a '(ver p. N)'; puntos guia a '— p. N'."""
        parts, prev = [], None
        for it in self.text_items:
            t = it.text
            piece = "\x00" + t.strip() + "\x01" if it.blue_num else t
            if prev is not None:
                gap = it.left - (prev.left + prev.w)
                parts.append(" " if (prev.text.endswith(" ") or t.startswith(" ") or gap >= 3) else "")
            parts.append(piece)
            prev = it
        s = "".join(parts)
        s = re.sub(r"[(（]\s*▷\s*Page\s*\x00(\d+)\x01\s*[)）]", r"(ver p. \1)", s)
        s = re.sub(r"\s*\x00(\d+)\x01", r" (ver p. \1)", s)
        s = re.sub(r"\s*\.{2,}\s*(\d+)", r" — p. \1", s)
        s = re.sub(r"\.{4,}", " ", s)
        self.text = normalize_text(s)
        return self.text


def make_lines(items: list[It]) -> list[Line]:
    lines: list[Line] = []
    cur = None
    for it in items:
        if (cur is not None and it.page == cur.page and abs(it.top - cur.items[0].top) <= 6
                and it.left > cur.items[-1].left - 2
                and it.left - (cur.items[-1].left + cur.items[-1].w) < 40
                and not ((cur.items[0].size >= 15 or it.size >= 15) and cur.items[0].size != it.size)):
            cur.add(it)
        else:
            cur = Line(it)
            lines.append(cur)
    return lines


def classify_line(ln: Line):
    t = ln.text
    if ln.size == 15 and t in LABELS:
        ln.kind = "label"
    elif ln.size >= 33 and ln.color == BLUE:
        ln.kind = "h3"
    elif ln.size in (17, 18, 19) and ln.color == BLUE:
        ln.kind = "h3"
    elif ln.size == 15 and ln.color == BLUE and not ln.has_bullet:
        ln.kind = "h4"
    elif ln.all_bold and len(t) <= 150 and not ln.has_bullet and not REF_END.search(t):
        ln.kind = "bold"
    else:
        ln.kind = "text"


# --------------------------------------------------------------------------- tablas


class Cell:
    def __init__(self, rect, items):
        self.rect = rect            # (xl, yt, xr, yb)
        self.items = items
        self.used = False
        self.r0 = self.r1 = self.c0 = self.c1 = 0
        self.txt = ""

    @property
    def header(self):
        return all(i.color == WHITE for i in self.items)


def split_by_rules(it: It, vs) -> list[It]:
    """Parte un item de texto que cruza una regla vertical (dos celdas leidas como una linea)."""
    xs = sorted(v[0] for v in vs if it.left + 4 < v[0] < it.left + it.w - 4 and v[1] - 2 <= it.cy <= v[2] + 2)
    text = it.text
    spaces = [i for i, c in enumerate(text) if c == " " and 0 < i < len(text) - 1]
    if not xs or not spaces or not text.strip():
        return [it]
    cuts = sorted({min(spaces, key=lambda i: abs(i + 0.5 - (x - it.left) / it.w * len(text))) for x in xs})
    out, prev = [], 0
    for c in cuts + [len(text)]:
        part = text[prev:c]
        if part.strip():
            p = It(it.page, it.top, round(it.left + it.w * prev / len(text)), round(it.w * len(part) / len(text)),
                   it.h, it.size, it.color, it.bold, part, it.href)
            p.blue_num = it.blue_num
            p.orig = it
            out.append(p)
        prev = c + 1
    return out


def find_cells(items, hs, vs):
    """Asigna cada item al rectangulo cerrado por reglas que lo rodea."""
    cells: dict[tuple, list[It]] = {}
    expanded: list[It] = []
    for it in items:
        expanded.extend(split_by_rules(it, vs))
    for it in expanded:
        cx, cy = it.cx, it.cy
        above = [h[0] for h in hs if h[0] < cy - 1 and h[1] - 2 <= cx <= h[2] + 2]
        below = [h[0] for h in hs if h[0] > cy + 1 and h[1] - 2 <= cx <= h[2] + 2]
        left = [v[0] for v in vs if v[0] < cx - 1 and v[1] - 2 <= cy <= v[2] + 2]
        right = [v[0] for v in vs if v[0] > cx + 1 and v[1] - 2 <= cy <= v[2] + 2]
        if above and below and left and right:
            rect = (round(max(left)), round(max(above)), round(min(right)), round(min(below)))
            if rect[2] - rect[0] <= 560 and rect[3] - rect[1] <= 700:
                cells.setdefault(rect, []).append(it)
    # un item partido solo se acepta si todos sus trozos cayeron en celdas
    placed = collections.Counter(id(i.orig) for its in cells.values() for i in its if i.orig is not None)
    total = collections.Counter(id(i.orig) for i in expanded if i.orig is not None)
    bad = {k for k in total if placed[k] != total[k]}
    if bad:
        for rect in list(cells):
            cells[rect] = [i for i in cells[rect] if i.orig is None or id(i.orig) not in bad]
            if not cells[rect]:
                del cells[rect]
    return cells


def group_tables(cells: dict) -> list[list[Cell]]:
    objs = [Cell(r, its) for r, its in sorted(cells.items())]
    parent = list(range(len(objs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def touch(a, b, tol=3):
        ox = min(a.rect[2], b.rect[2]) - max(a.rect[0], b.rect[0])
        oy = min(a.rect[3], b.rect[3]) - max(a.rect[1], b.rect[1])
        return (ox >= -tol and oy > tol) or (oy >= -tol and ox > tol)

    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            if touch(objs[i], objs[j]):
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i, o in enumerate(objs):
        groups[find(i)].append(o)
    return [g for _, g in sorted(groups.items())]


def _cluster(vals, tol=3):
    out = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def _nearest(edges, v):
    return min(range(len(edges)), key=lambda k: abs(edges[k] - v))


def cell_text(cell: Cell, vocab) -> str:
    its = sorted(cell.items, key=lambda i: (round(i.top / 4), i.left))
    out, prev = "", None
    for ln in make_lines(its):
        text = ln.build()
        if (prev is not None and ln.top - prev.top >= 23 and not cell.header and out
                and (out[-1] in ")]" or out[-1].isdigit() or out[-1].isupper()) and text[:1] not in "[("):
            out = out + " / "   # varios valores completos en una misma celda (interlineado mayor)
            out += text
        else:
            out = join_line(out, text, vocab)
        prev = ln
    return out


def table_rows(cells: list[Cell], vocab):
    """Filas de la tabla como listas de (campo, [(texto, celda)...]) con la cabecera como campo."""
    xs = _cluster([c.rect[0] for c in cells] + [c.rect[2] for c in cells])
    ys = _cluster([c.rect[1] for c in cells] + [c.rect[3] for c in cells])
    for c in cells:
        c.c0, c.c1 = _nearest(xs, c.rect[0]), _nearest(xs, c.rect[2])
        c.r0, c.r1 = _nearest(ys, c.rect[1]), _nearest(ys, c.rect[3])
        c.txt = cell_text(c, vocab)
    nrows = len(ys) - 1
    header_rows = 0
    for r in range(nrows):
        starting = [c for c in cells if c.r0 == r]
        if starting and all(c.header for c in starting):
            header_rows = max(c.r1 for c in starting)
        else:
            break
    hdr = sorted([c for c in cells if c.header and c.r0 < header_rows], key=lambda c: (c.r0, c.c0))
    rows = []
    for r in range(header_rows, nrows):
        row_cells = sorted([c for c in cells if c.r0 <= r < c.r1 and c not in hdr], key=lambda c: c.c0)
        if not row_cells:
            continue
        grouped = []
        for c in row_cells:
            labels = []
            for h in hdr:
                if h.c0 < c.c1 and c.c0 < h.c1 and h.txt and (not labels or labels[-1] != h.txt):
                    labels.append(h.txt)
            label = " › ".join(labels)
            if grouped and grouped[-1][0] == label and label:
                grouped[-1][1].append(c)
            else:
                grouped.append((label, [c]))
        rows.append(grouped)
    return rows, hdr


# --------------------------------------------------------------------------- bloques


class Seg:
    """Fragmento de texto de salida con su pagina de origen (None = marcado anadido)."""
    __slots__ = ("text", "page", "count")

    def __init__(self, text, page, count=True):
        self.text, self.page, self.count = text, page, count


class Block:
    def __init__(self, kind, level=0, label=None):
        self.kind = kind            # heading | para | item | callout | table | marker
        self.segs: list[Seg] = []
        self.level = level
        self.label = label
        self.children: list[Block] = []
        self.rows = None
        self.hdr = []
        self.pages: set[int] = set()
        self.last_line: Line | None = None
        self.src_lines: list[Line] = []
        self.from_bold = False


def seg_text(segs):
    return "".join(s.text for s in segs)


class Builder:
    """Convierte las lineas de una seccion en bloques (titulos, parrafos, avisos, tablas)."""

    def __init__(self, vocab, stats, infos, markers=True):
        self.vocab, self.stats, self.infos, self.markers = vocab, stats, infos, markers
        self.blocks: list[Block] = []
        self.cur: Block | None = None
        self.callout: Block | None = None
        self.callout_end = None
        self.callout_pos = None
        self.last_page = None
        self.pending = None
        self.legend_run = False
        self.fig_seen = False
        self.dropped_blocks: list[Block] = []

    # ----- utilidades internas -----
    def _container(self):
        return self.callout.children if self.callout is not None else self.blocks

    def _marker(self):
        if self.markers and self.pending is not None and self.callout is None:
            num = self.infos[self.pending].printed_eff
            self.blocks.append(Block_marker(f"[p. {num}]"))
        if self.callout is None:
            self.pending = None

    def _new(self, kind, line, level=0):
        self._marker()
        b = Block(kind, level=level)
        b.pages.add(line.page)
        self._container().append(b)
        self.cur = b
        return b

    def _append(self, b: Block, line: Line):
        text = line.text
        if not b.segs:
            b.segs.append(Seg(text, line.page))
        else:
            prev = seg_text(b.segs)
            joined = join_line(prev, text, self.vocab, self.stats)
            if joined == prev + " " + text:
                b.segs.append(Seg(" " + text, line.page))
            elif joined == prev + text:            # guion conservado (compuesto)
                b.segs.append(Seg(text, line.page))
            else:                                  # guion de corte de palabra: se elimina
                b.segs[-1].text = b.segs[-1].text[:-1]
                b.segs.append(Seg(text, line.page))
        b.pages.add(line.page)
        b.src_lines.append(line)
        b.last_line = line

    def close_callout(self):
        self.cur = None
        self.callout = None
        self.callout_end = None

    # ----- API -----
    def start_page(self, page):
        if page != self.last_page:
            self.pending = page
            self.last_page = page

    def _rule_below(self, line: Line, y0: float):
        best = None
        for (y, x1, x2, _w) in self.infos[line.page].rules_callout:
            if y > y0 and x1 - 12 <= line.left <= x2 and (best is None or y < best[3]):
                best = (line.page, x1, x2, y)
        return best

    def _starts_new(self, line: Line, cur: Block) -> bool:
        text, last, ptext = line.text, cur.last_line, seg_text(cur.segs)
        if line.has_bullet or text[:1] in CIRC:
            return True
        if REF_END.search(ptext):
            return True
        if last.page == line.page and last.col == line.col and line.top > last.top:
            if line.top - last.top > 22.5:
                # un parrafo no empieza en minuscula: iconos en linea agrandan el interlineado
                return not (text[:1].islower() and not ptext.endswith(SENT_END))
            return ptext.endswith(":") and text[:1].isupper()
        # salto de columna o de pagina: continua solo si la frase quedo abierta
        open_ = ptext.endswith("-") or not ptext.endswith(SENT_END)
        return not (open_ and (text[:1].islower() or ptext.endswith("-")))

    def add_line(self, line: Line, entry=False, entry_left=None):
        self.start_page(line.page)
        kind = line.kind
        text = line.text
        if entry and kind in ("bold", "h4"):
            kind = "text"
        # fin de recuadro de aviso: por su filete inferior o por cambio de columna/pagina
        if self.callout is not None and kind != "label":
            pos = (line.page, line.col)
            if pos != self.callout_pos:
                if self.callout_end is not None:
                    self.close_callout()          # el filete ya cerro el recuadro
                else:
                    self.callout_pos = pos        # el recuadro continua en la nueva columna/pagina
                    self.callout_end = self._rule_below(line, line.top - 4)
            if self.callout is not None and self.callout_end is not None:
                pg, x1, x2, y = self.callout_end
                if line.page == pg and line.top > y and x1 - 12 <= line.left <= x2:
                    self.close_callout()
        if kind == "bold":
            cur = self.cur
            inline = (self.callout is not None) or (
                cur is not None and cur.kind in ("para", "item") and cur.last_line is not None
                and cur.last_line.page == line.page and cur.last_line.col == line.col
                and 0 < line.top - cur.last_line.top <= 22.5)
            if inline:
                kind = "text"
        if kind in ("h3", "h4", "bold"):
            self._heading(line, 4 if kind == "bold" else int(kind[1]), from_bold=(kind == "bold"))
            return
        if kind == "label":
            self.cur = None
            self.close_callout()
            self._marker()
            c = Block("callout", label=text)
            c.pages.add(line.page)
            self.blocks.append(c)
            self.callout = c
            self.callout_pos = (line.page, line.col)
            self.callout_end = self._rule_below(line, line.top)
            self.legend_run = False
            return
        starts_circ = text[:1] in CIRC
        cur = self.cur
        if entry:
            new = cur is None or not (not REF_END.search(seg_text(cur.segs)) and (
                seg_text(cur.segs).endswith("-") or text[:1].islower() or text[:1].isdigit()))
            if cur is not None and text.startswith("— p."):
                new = False
        elif cur is None or cur.kind not in ("para", "item"):
            new = True
        else:
            new = self._starts_new(line, cur)
        if not new:
            self._append(cur, line)
            return
        ptext = seg_text(cur.segs) if cur is not None else ""
        nested = False
        if not entry and self.legend_run and not starts_circ and not line.has_bullet:
            nested = bool(ptext.endswith(":") or (cur is not None and cur.kind == "item" and cur.level == 1))
            if not nested:
                self.legend_run = False
        is_item = entry or line.has_bullet or starts_circ or nested
        if starts_circ:
            self.legend_run = True
        b = self._new("item" if is_item else "para", line)
        if entry:
            b.level = 1 if line.left > entry_left[line.col] else 0
        elif nested:
            b.level = 1
        self._append(b, line)

    def _heading(self, line: Line, level: int, from_bold=False):
        self.cur = None
        self.legend_run = False
        cont = self._container()
        last = cont[-1] if cont and cont[-1].kind == "heading" else None
        if (last is not None and last.level == level and last.last_line is not None
                and last.last_line.page == line.page and last.last_line.col == line.col
                and 0 < line.top - last.last_line.top <= 25 and last.last_line.kind == line.kind
                and last.last_line.size == line.size):
            self._append(last, line)
            return
        self.close_callout()
        self._marker()
        b = Block("heading", level=level)
        b.from_bold = from_bold
        b.pages.add(line.page)
        self.blocks.append(b)
        self._append(b, line)

    def add_table(self, rows, hdr, page):
        self.cur = None
        self.legend_run = False
        self.close_callout()
        self.start_page(page)
        self._marker()
        b = Block("table")
        b.rows, b.hdr = rows, hdr
        b.pages.add(page)
        self.blocks.append(b)

    def add_figure(self, page):
        """Marca [figura no incluida] solo la primera vez en la seccion."""
        self.start_page(page)
        if not self.fig_seen:
            self.fig_seen = True
            self.cur = None
            self._marker()
            self.blocks.append(Block_marker("[figura no incluida]"))

    def finish(self):
        self.cur = None
        self.close_callout()
        self._bold_headings()
        # quitar el aviso repetido "Equipamiento del vehiculo ..." (se conserva el de la p. 5)
        out = []
        for i, b in enumerate(self.blocks):
            if b.kind == "para":
                nl = norm_letters(seg_text(b.segs))
                if nl.startswith(NOTICE_START) and nl.endswith(NOTICE_END) and len(nl) < 700:
                    self.dropped_blocks.append(b)
                    if out and out[-1].kind == "heading" and norm_letters(seg_text(out[-1].segs)) == NOTICE_HEADING:
                        self.dropped_blocks.append(out.pop())
                    continue
            out.append(b)
        self.blocks = out

    def _bold_headings(self):
        """Un bloque en negrita es titulo solo si es corto y no termina como una frase."""
        merged: list[Block] = []
        for b in self.blocks:
            prev = merged[-1] if merged else None
            if (b.kind == "heading" and b.from_bold and prev is not None and prev.kind == "heading"
                    and prev.from_bold and seg_text(b.segs).strip()[:1].islower()):
                for ln in b.src_lines:
                    self._append(prev, ln)
                continue
            merged.append(b)
        for b in merged:
            if b.kind == "heading" and b.from_bold:
                t = seg_text(b.segs).strip()
                if len(t) > 110 or t.endswith((".", ":", ";", ",")):
                    b.kind = "para"
        self.blocks = merged


def Block_marker(text):
    b = Block("marker")
    b.segs.append(Seg(text, None, False))
    return b


# --------------------------------------------------------------------------- pipeline


def assign_sections(n_pages, infos):
    """Secciones por la banda superior (titulo de seccion) y paginas especiales."""
    front = {"title": "Introducción y consejos de seguridad", "chapter": 0, "pages": [], "key": "intro"}
    cont = {"title": "Contenido del manual", "chapter": 0, "pages": [], "key": "contenido"}
    sections = [front, cont]
    cur = None
    for n in range(1, n_pages + 1):
        info = infos[n]
        if n == 1:
            info.kind = "portada"
        if n <= 11:
            front["pages"].append(n)
            info.sec = 0
            continue
        if n <= 19 or info.opener or (info.chapter_digit is None and info.leaders):
            info.kind = "toc"
            cont["pages"].append(n)
            info.sec = 1
            continue
        if info.band:
            cur = {"title": info.band, "chapter": None, "pages": [], "key": "sec"}
            sections.append(cur)
        if cur is None:
            raise SystemExit(f"No hay seccion para la pagina {n}")
        cur["pages"].append(n)
        info.sec = sections.index(cur)
        if info.chapter_digit is not None:
            cur["chapter"] = info.chapter_digit
    last = 0
    for s in sections[2:]:
        if s["chapter"] is None:
            s["chapter"] = last
        last = s["chapter"]
    return sections


def process(pdf: str, jobs: int = 8):
    n_pages, raw_pages, items = load_pages(pdf)
    infos = {n: PageInfo(n) for n in range(1, n_pages + 1)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
        rules = dict(zip(range(1, n_pages + 1), ex.map(lambda n: load_rules(pdf, n), range(1, n_pages + 1))))

    # ---- mobiliario de pagina y portada ----
    cover_tokens, seen = [], set()
    for n in range(1, n_pages + 1):
        if n == 1:
            for it in items[1]:
                s = it.text.strip()
                if not s:
                    it.cat = "espacio"
                elif CJK.search(s):
                    it.cat = "texto_chino"
                elif s in seen:
                    it.cat = "portada_repetida"
                else:
                    seen.add(s)
                    cover_tokens.append(s)
        else:
            classify_items(infos[n], items[n])
    cover_text = " ".join(cover_tokens)
    sections = assign_sections(n_pages, infos)

    # ---- vocabulario de compuestos con guion (palabras con guion en mitad de linea) ----
    vocab = set()
    for n in range(2, n_pages + 1):
        for it in items[n]:
            if it.cat is None:
                body = it.text.rstrip()
                for m in HYPH_WORD.finditer(body):
                    vocab.add(m.group(0).lower())
    for n in range(2, n_pages + 1):
        for it in items[n]:
            if (it.cat is None and it.size == 13 and it.color == BLUE
                    and re.fullmatch(r"\d{1,3}", it.text.strip())):
                it.blue_num = True

    stats = collections.Counter()
    builders = {si: Builder(vocab, stats, infos, markers=(sections[si]["key"] != "contenido"))
                for si in range(len(sections))}

    # ---- portada ----
    infos[1].kept_norm.update(alnum_counter(cover_text))
    b = Block("para")
    b.segs.append(Seg("Portada del manual: ", None, False))
    b.segs.append(Seg(cover_text, 1))
    b.pages.add(1)
    builders[0].blocks.append(b)

    # ---- por pagina ----
    sec_blocks_pre = collections.defaultdict(int)
    for n in range(2, n_pages + 1):
        info = infos[n]
        hs, vs = rules[n]
        info.rules_callout = [h for h in hs if 0.45 <= h[3] <= 0.55 and h[2] - h[1] >= 120]
        content = [i for i in items[n] if i.cat is None]
        order = {id(it): k for k, it in enumerate(items[n])}
        tbl_ids, tables = set(), []
        if info.kind == "contenido":
            thin_h = [h for h in hs if h[3] <= 0.3]
            thin_v = [v for v in vs if v[3] <= 0.3]
            if thin_h and thin_v:
                for group in group_tables(find_cells(content, thin_h, thin_v)):
                    if len(group) < 2:
                        continue
                    rows, hdr = table_rows(group, vocab)
                    first = min(order[id(i.orig or i)] for c in group for i in c.items)
                    tables.append((first, group, rows, hdr))
                    for c in group:
                        tbl_ids.update(id(i.orig or i) for i in c.items)
                        info.kept_norm.update(alnum_counter(c.txt))
        info.tables = len(tables)
        flow = [it for it in items[n] if it.cat is None and id(it) not in tbl_ids]
        lines = make_lines(flow)
        for ln in lines:
            ln.build()
            ln.order = order[id(ln.items[0])]
            classify_line(ln)
            info.kept_norm.update(alnum_counter(ln.text))
        if info.band:
            info.kept_norm.update(alnum_counter(info.band))
        if info.opener and info.chapter_digit is not None:
            info.kept_norm.update(alnum_counter(str(info.chapter_digit)))
        stream = ([(ln.order, 0, "line", ln) for ln in lines] + [(t[0], 1, "table", t) for t in tables]
                  + [(order[id(i)], 2, "figure", i) for i in items[n] if i.fig])
        stream.sort(key=lambda x: (x[0], x[1]))
        info.figures = sum(1 for s in stream if s[2] == "figure")

        bld = builders[info.sec]
        toc_entries = info.kind == "toc" and info.leaders
        index_page = sections[info.sec]["chapter"] == 8
        if n in range(13, 20):
            entry_left = {0: 121, 1: 384}
        else:
            entry_left = {c: min([ln.left for ln in lines if ln.kind == "text" and ln.col == c] or [0]) + 6
                          for c in (0, 1)}
        if info.opener and info.chapter_digit is not None:
            bld.start_page(n)
            hd = Block("heading", level=3)
            hd.segs.append(Seg("Capítulo ", None, False))
            hd.segs.append(Seg(str(info.chapter_digit), n))
            hd.segs.append(Seg(": ", None, False))
            hd.segs.append(Seg(info.band, n))
            hd.pages.add(n)
            bld.blocks.append(hd)
        for _o, _k, kind, obj in stream:
            if kind == "line":
                entry = (toc_entries or index_page) and obj.kind != "h3"
                bld.add_line(obj, entry=entry, entry_left=entry_left)
            elif kind == "table":
                bld.add_table(obj[2], obj[3], n)
            else:
                bld.add_figure(n)
    for b in builders.values():
        b.finish()

    # ---- contabilidad de entrada y avisos repetidos ----
    for n in range(1, n_pages + 1):
        info = infos[n]
        for it in items[n]:
            if it.cat is not None:
                info.dropped[it.cat] += nonspace(it.text)
            else:
                info.kept_src += nonspace(it.text)
    for bld in builders.values():
        for blk in bld.dropped_blocks:
            for ln in blk.src_lines:
                pg = ln.page
                n_src = sum(nonspace(i.text) for i in ln.items)
                infos[pg].kept_src -= n_src
                infos[pg].dropped["aviso_repetido_equipamiento"] += n_src
                infos[pg].kept_norm.subtract(alnum_counter(ln.text))
    return dict(n_pages=n_pages, raw_pages=raw_pages, items=items, infos=infos, sections=sections,
                builders=builders, stats=stats, cover_text=cover_text)


# --------------------------------------------------------------------------- render


def count_segs(segs, infos):
    for s in segs:
        if s.page is not None:
            info = infos[s.page]
            info.chars_out += len(s.text)
            info.chars_out_nospace += nonspace(s.text)
            if s.count:
                info.out.update(alnum_counter(s.text))


def render_block(b: Block, infos, count=True) -> list[str]:
    """Devuelve las lineas de texto del bloque (cuenta caracteres por pagina)."""
    if b.kind == "marker":
        return [seg_text(b.segs)]
    if b.kind == "heading":
        if count:
            count_segs(b.segs, infos)
        return ["#" * b.level + " " + seg_text(b.segs).strip()]
    if b.kind == "para":
        if count:
            count_segs(b.segs, infos)
        return [seg_text(b.segs).strip()]
    if b.kind == "item":
        if count:
            count_segs(b.segs, infos)
        return ["  " * b.level + "- " + seg_text(b.segs).strip()]
    if b.kind == "table":
        lines = []
        pg = next(iter(b.pages))
        for h in b.hdr:
            if not h.used:
                h.used = True
                count_segs([Seg(h.txt, pg)], infos)
        for grouped in b.rows:
            chunks = []
            for label, cells in grouped:
                vals = []
                for c in cells:
                    dup = c.used
                    c.used = True
                    count_segs([Seg(c.txt, pg, not dup)], infos)
                    vals.append(c.txt)
                text = " › ".join(v for v in vals if v)
                chunks.append(f"{label}: {text}" if label else text)
            if (any(h.txt == "Iconos" for h in b.hdr)
                    and not any(lb == "Iconos" for lb, _ in grouped)):
                chunks.insert(0, "Iconos: [icono no incluido]")   # la columna de iconos son imagenes
            lines.append("- " + "; ".join(chunks))
        return lines
    if b.kind == "callout":
        kids = b.children
        first_para = bool(kids) and kids[0].kind == "para"
        if count:
            count_segs([Seg(b.label, next(iter(b.pages)))], infos)
        if first_para:
            count_segs(kids[0].segs, infos) if count else None
            out = [f"**{b.label}:** " + seg_text(kids[0].segs).strip()]
            rest = kids[1:]
        else:
            out = [f"**{b.label}:**"]
            rest = kids
        prev = None
        for k in rest:
            if prev is not None and not (k.kind == "item" and prev.kind == "item"):
                out.append("")
            elif prev is None and k.kind == "para":
                out.append("")
            out.extend(render_block(k, infos, count))
            prev = k
        return ["> " + ln if ln else ">" for ln in out]
    return []


def render_blocks(blocks: list[Block], infos) -> str:
    chunks: list[str] = []
    prev = None
    for b in blocks:
        lines = render_block(b, infos)
        if not lines:
            continue
        text = "\n".join(lines)
        if prev is not None and b.kind in ("item", "table") and prev.kind == b.kind:
            chunks[-1] += "\n" + text
        else:
            chunks.append(text)
        prev = b
    return "\n\n".join(chunks)


def build_docs(R):
    infos, sections, builders = R["infos"], R["sections"], R["builders"]
    units = []   # (seccion, parte, texto, paginas)
    for si, sec in enumerate(sections):
        blocks = list(builders[si].blocks)
        if sec["key"] == "sec":
            if LIGHT_SECTION.search(sec["title"]):
                note = Block("para")
                note.segs.append(Seg(LIGHT_NOTE, None, False))
                has_fig = any(b.kind == "marker" and "figura" in seg_text(b.segs) for b in blocks)
                if not has_fig:
                    blocks.insert(0, Block_marker("[figura no incluida]"))
                blocks.insert(1 if not has_fig else 0, note)
        # trozos por tamano (cortes en titulos de nivel 3 y, si hace falta, entre bloques)
        groups, cur = [], []
        for b in blocks:
            if b.kind == "heading" and b.level <= 3 and cur:
                groups.append(cur)
                cur = []
            cur.append(b)
        if cur:
            groups.append(cur)
        rendered = []
        for g in groups:
            # los marcadores de pagina no deben quedar solos al final de un grupo
            rendered.append((g, None))
        parts, size, part_blocks = [], 0, []
        head_len = len(sec["title"]) + 8
        for g, _ in rendered:
            for sub in _split_group(g, infos):
                sz = sum(len(l) + 2 for b in sub for l in block_preview(b))
                if part_blocks and size + sz + head_len > MAX_DOC_BYTES:
                    parts.append(part_blocks)
                    part_blocks, size = [], 0
                part_blocks = part_blocks + sub
                size += sz
        if part_blocks:
            parts.append(part_blocks)
        for pi, pb in enumerate(parts):
            units.append({"sec": si, "part": pi + 1, "parts": len(parts), "blocks": pb})
    return units


def block_preview(b: Block) -> list[str]:
    """Texto aproximado del bloque para estimar tamano (sin contar caracteres)."""
    if b.kind == "table":
        return ["- " + "; ".join((f"{lb}: " if lb else "") + " › ".join(c.txt for c in cs) for lb, cs in g)
                for g in b.rows]
    if b.kind == "callout":
        out = [b.label]
        for k in b.children:
            out.extend(block_preview(k))
        return out
    return [seg_text(b.segs)]


def _split_group(g: list[Block], infos):
    """Si un grupo (titulo + contenido) es enorme lo parte entre bloques."""
    total = sum(len(l) + 2 for b in g for l in block_preview(b))
    if total <= MAX_DOC_BYTES - 2000:
        return [g]
    subs, cur, size = [], [], 0
    for b in g:
        sz = sum(len(l) + 2 for l in block_preview(b))
        if cur and size + sz > MAX_DOC_BYTES - 4000 and b.kind in ("heading", "para", "callout"):
            subs.append(cur)
            cur, size = [], 0
        cur.append(b)
        size += sz
    if cur:
        subs.append(cur)
    return subs


def page_set(blocks: list[Block]) -> set[int]:
    pages = set()
    for b in blocks:
        pages |= b.pages
        pages |= page_set(b.children)
    return pages


def compose_docs(R):
    infos, sections = R["infos"], R["sections"]
    units = build_docs(R)
    # ---- fusionar unidades contiguas del mismo capitulo ----
    for u in units:
        sec = sections[u["sec"]]
        u["chapter"] = sec["chapter"]
        u["size"] = sum(len(l) + 2 for b in u["blocks"] for l in block_preview(b)) + len(sec["title"]) + 10
    docs: list[list[dict]] = []
    for u in units:
        if (docs and docs[-1][0]["chapter"] == u["chapter"] and u["chapter"] != 0
                and sum(x["size"] for x in docs[-1]) < FUSE_TO
                and sum(x["size"] for x in docs[-1]) + u["size"] <= MAX_DOC_BYTES - 1500
                and docs[-1][-1]["part"] == docs[-1][-1]["parts"] and u["part"] == 1):
            docs[-1].append(u)
        else:
            docs.append([u])
    # documentos todavia pequenos: unir con el vecino del mismo capitulo si cabe
    changed = True
    while changed:
        changed = False
        for i, d in enumerate(docs):
            size = sum(x["size"] for x in d)
            if size >= SOFT_MIN or d[0]["chapter"] == 0:
                continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(docs) and docs[j][0]["chapter"] == d[0]["chapter"]:
                    other = sum(x["size"] for x in docs[j])
                    if size + other <= MAX_DOC_BYTES - 1500:
                        lo, hi = min(i, j), max(i, j)
                        docs[lo] = docs[lo] + docs[hi]
                        del docs[hi]
                        changed = True
                        break
            if changed:
                break
    # ---- nombres, front matter y render ----
    out = []
    used = set()
    seq = collections.Counter()
    for d in docs:
        ch = d[0]["chapter"]
        titles = []
        for u in d:
            t = sections[u["sec"]]["title"]
            if not titles or titles[-1] != t:
                titles.append(t)
        if ch == 0:
            base = "00-" + slugify(titles[0], 48)
            chapter_label = "Introducción" if sections[d[0]["sec"]]["key"] == "intro" else "Contenido"
            chapter_name = chapter_label
        else:
            base = f"{ch:02d}-{CHAPTER_SLUG[ch]}-"
            if len(titles) == 1:
                base += slugify(titles[0], 60)
            elif len(titles) == 2:
                base += slugify(titles[0], 38) + "-y-" + slugify(titles[1], 38)
            else:
                base += slugify(titles[0], 30) + "-a-" + slugify(titles[-1], 30)
            chapter_name = f"{ch} {CHAPTERS[ch]}"
        parts_total = d[0]["parts"] if len(d) == 1 else 1
        if len(d) == 1 and d[0]["parts"] > 1:
            base += f"-parte-{d[0]['part']}"
        name = base
        seq[name] += 1
        if name in used:
            name = f"{base}-{seq[name]}"
        used.add(name)
        blocks_all = [b for u in d for b in u["blocks"]]
        pages = sorted(page_set(blocks_all))
        if ch == 0 and sections[d[0]["sec"]]["key"] == "contenido":
            pages = sorted(set(pages) | set(sections[d[0]["sec"]]["pages"]))
        printed = sorted({infos[p].printed_eff for p in pages if infos[p].printed_eff is not None})
        title_core = "; ".join(titles)
        if len(d) == 1 and d[0]["parts"] > 1:
            title_core += f" (parte {d[0]['part']} de {d[0]['parts']})"
        title = f"Manual Haval H6 — {chapter_name} › {title_core}" if ch else f"Manual Haval H6 — {title_core}"
        fm = ["---",
              f"titulo: {json.dumps(title, ensure_ascii=False)}",
              f"modelo: {json.dumps(MODEL, ensure_ascii=False)}",
              f"capitulo: {json.dumps(chapter_name, ensure_ascii=False)}",
              f"secciones: {json.dumps(titles, ensure_ascii=False)}",
              f"paginas_pdf: {json.dumps(ranges(pages))}",
              f"paginas_impresas: {json.dumps(ranges(printed))}",
              f"fuente: {json.dumps(f'{SOURCE_NAME}, edición {SOURCE_EDITION} (introducción fechada 06/09/2021)', ensure_ascii=False)}",
              'idioma: "es"',
              "---"]
        body = [f"# {title}",
                f"Fuente: Manual de usuario del Haval H6 ({SOURCE_NAME}, edición {SOURCE_EDITION}), "
                f"páginas impresas {ranges(printed)} (páginas del PDF {ranges(pages)}).",
                "Los marcadores [p. N] y las remisiones (ver p. N) usan el número de página impreso del manual "
                "(página del PDF = página impresa + 3)."]
        for u in d:
            sec = sections[u["sec"]]
            heading_pages = [p for p in sec["pages"] if infos[p].band and infos[p].kind == "contenido"]
            h = Block("heading", level=2)
            suffix = f" (parte {u['part']} de {u['parts']})" if u["parts"] > 1 else ""
            if sec["key"] == "sec" and heading_pages and u["part"] == 1:
                h.segs = [Seg(sec["title"], heading_pages[0]), Seg(suffix, None, False)]
                h.pages.add(heading_pages[0])
            else:
                h.segs = [Seg(sec["title"] + suffix, None, False)]
            body.append("\n".join(render_block(h, infos)))
            body.append(render_blocks(u["blocks"], infos))
        text = "\n".join(fm) + "\n" + "\n\n".join(x for x in body if x) + "\n"
        out.append({"name": name + ".md", "text": text, "pages": pages, "printed": printed,
                    "chapter": ch, "titles": titles})
    return out


# --------------------------------------------------------------------------- cobertura


def build_report(pdf, R, docs):
    infos, raw_pages, n_pages = R["infos"], R["raw_pages"], R["n_pages"]
    pdf_bytes = Path(pdf).read_bytes()
    page_docs = collections.defaultdict(list)
    for d in docs:
        for p in d["pages"]:
            page_docs[p].append(d["name"])
    pages_out, problems = [], []
    tot_in = tot_out = tot_in_ns = tot_out_ns = 0
    for n in range(1, n_pages + 1):
        info = infos[n]
        raw = raw_pages[n - 1]
        in_chars = len(raw.replace("\f", ""))
        in_ns = nonspace(raw)
        as_title = sum(v for k, v in info.dropped.items() if k in AS_TITLE)
        dropped = {k: v for k, v in sorted(info.dropped.items()) if k not in AS_TITLE and v}
        balance_in = in_ns == info.kept_src + sum(info.dropped.values())
        diff = (+info.kept_norm) - (+info.out)
        diff2 = (+info.out) - (+info.kept_norm)
        balance_out = not diff and not diff2
        no_content = info.kept_src + as_title == 0
        placed = bool(page_docs.get(n))
        if not no_content and not placed:
            problems.append(f"pagina {n}: con contenido pero sin ubicar")
        if not balance_in:
            problems.append(f"pagina {n}: entrada != conservado + descartado "
                            f"({in_ns} vs {info.kept_src + sum(info.dropped.values())})")
        if not balance_out:
            problems.append(f"pagina {n}: salida distinta de lo conservado (falta {dict(diff)}, sobra {dict(diff2)})")
        pages_out.append({
            "pdf": n,
            "impresa": info.printed_eff,
            "impresa_inferida": info.printed is None and info.printed_eff is not None,
            "tipo": info.kind,
            "seccion": R["sections"][info.sec]["title"] if info.sec is not None else None,
            "documentos": page_docs.get(n, []),
            "sin_texto": no_content,
            "texto_escaso": in_ns < 100,
            "caracteres_entrada": in_chars,
            "caracteres_entrada_sin_espacios": in_ns,
            "caracteres_salida": info.chars_out,
            "caracteres_salida_sin_espacios": info.chars_out_nospace,
            "conservado_sin_espacios": info.kept_src,
            "conservado_como_titulo": as_title,
            "descartado": dropped,
            "tablas": info.tables,
            "figuras_marcadas": info.figures,
            "contabilidad_entrada_ok": balance_in,
            "contenido_salida_completo": balance_out,
        })
        tot_in += in_chars
        tot_in_ns += in_ns
        tot_out += info.chars_out
        tot_out_ns += info.chars_out_nospace
    md_bytes = sum(len(d["text"].encode("utf-8")) for d in docs)
    desfases = collections.Counter(
        infos[n].n - infos[n].printed for n in range(1, n_pages + 1) if infos[n].printed is not None)
    dropped_total, as_title_total = collections.Counter(), 0
    for info in infos.values():
        for k, v in info.dropped.items():
            if k in AS_TITLE:
                as_title_total += v
            elif v:
                dropped_total[k] += v
    figure_codes = sum(1 for n in infos for it in R["items"][n] if it.fig)
    with_text = [p for p in pages_out if not p["sin_texto"]]
    summary = {
        "paginas_totales": n_pages,
        "paginas_con_texto": len(with_text),
        "paginas_sin_texto": n_pages - len(with_text),
        "paginas_sin_texto_lista": [p["pdf"] for p in pages_out if p["sin_texto"]],
        "paginas_con_poco_texto_lt100": [p["pdf"] for p in pages_out if p["texto_escaso"]],
        "paginas_sin_ubicar": sum(1 for p in with_text if not p["documentos"]),
        "paginas_sin_ubicar_lista": [p["pdf"] for p in with_text if not p["documentos"]],
        "caracteres_entrada": tot_in,
        "caracteres_entrada_sin_espacios": tot_in_ns,
        "caracteres_salida": tot_out,
        "caracteres_salida_sin_espacios": tot_out_ns,
        "descartado_por_categoria_sin_espacios": dict(sorted(dropped_total.items())),
        "conservado_como_titulo_sin_espacios": as_title_total,
        "codigos_de_figura_detectados": figure_codes,
        "tablas_reconstruidas": sum(info.tables for info in infos.values()),
        "uniones_de_guion": dict(sorted(R["stats"].items())),
        "documentos": len(docs),
        "bytes_md_total": md_bytes,
        "limite_bytes": LIMIT_BYTES,
        "holgura_bytes": LIMIT_BYTES - md_bytes,
        "holgura_porcentaje": round(100 * (LIMIT_BYTES - md_bytes) / LIMIT_BYTES, 1),
        "desfase_pdf_menos_impresa": dict(sorted(desfases.items())),
        "paginas_con_tablas": [p["pdf"] for p in pages_out if p["tablas"]],
        "paginas_con_figuras": [p["pdf"] for p in pages_out if p["figuras_marcadas"]],
        "problemas": problems,
    }
    doc_info = {d["name"]: {"bytes": len(d["text"].encode("utf-8")), "paginas_pdf": d["pages"],
                            "paginas_impresas": d["printed"]} for d in docs}
    return {
        "fuente": {"archivo": Path(pdf).name, "bytes": len(pdf_bytes),
                   "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                   "manual": SOURCE_NAME, "edicion": SOURCE_EDITION},
        "resumen": summary,
        "documentos": doc_info,
        "paginas": pages_out,
    }, problems


# --------------------------------------------------------------------------- principal


def generate(pdf: str, jobs: int = 8):
    R = process(pdf, jobs)
    docs = compose_docs(R)
    report, problems = build_report(pdf, R, docs)
    files = {d["name"]: d["text"] for d in docs}
    files["_cobertura.json"] = json.dumps(report, ensure_ascii=False, indent=1) + "\n"
    return files, report, problems


def check_files(files: dict[str, str], report: dict, problems: list[str]) -> list[str]:
    errs = list(problems)
    total = 0
    for name, text in files.items():
        if not name.endswith(".md"):
            continue
        size = len(text.encode("utf-8"))
        total += size
        if size < MIN_BYTES:
            errs.append(f"{name}: {size} bytes (< {MIN_BYTES})")
        if size > MAX_DOC_BYTES:
            errs.append(f"{name}: {size} bytes (> {MAX_DOC_BYTES})")
        if CJK.search(text):
            errs.append(f"{name}: contiene caracteres chinos")
        for m in re.finditer(r"[a-záéíóúüñ]-(?: |\n)[a-záéíóúüñ]", text):
            errs.append(f"{name}: palabra cortada residual cerca de {text[max(0, m.start() - 20):m.end() + 20]!r}")
            break
    if total >= LIMIT_BYTES:
        errs.append(f"total {total} bytes >= {LIMIT_BYTES}")
    if report["resumen"]["paginas_sin_ubicar"]:
        errs.append("hay paginas sin ubicar")
    return errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", help="ruta al PDF del manual (no se copia al repositorio)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "knowledge" / "manual-h6"),
                    help="carpeta de salida (por defecto knowledge/manual-h6)")
    ap.add_argument("--check", action="store_true",
                    help="solo verifica: no escribe; compara con lo que hay en --out y valida invariantes")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args(argv)
    if not Path(args.pdf).is_file():
        print(f"No existe el PDF: {args.pdf}", file=sys.stderr)
        return 2
    files, report, problems = generate(args.pdf, args.jobs)
    out = Path(args.out)
    s = report["resumen"]
    print(f"{s['documentos']} documentos, {s['bytes_md_total']} bytes "
          f"(holgura {s['holgura_bytes']} bytes frente a {LIMIT_BYTES}); "
          f"paginas {s['paginas_totales']}: con texto {s['paginas_con_texto']}, "
          f"sin texto {s['paginas_sin_texto']}, sin ubicar {s['paginas_sin_ubicar']}")
    errs = check_files(files, report, problems)
    if args.check:
        existing = {p.name for p in out.glob("[0-9][0-9]-*.md")} | ({"_cobertura.json"} if (out / "_cobertura.json").exists() else set())
        for name, text in files.items():
            p = out / name
            if not p.exists():
                errs.append(f"falta en disco: {name}")
            elif p.read_text(encoding="utf-8") != text:
                errs.append(f"distinto en disco: {name}")
        for extra in sorted(existing - set(files)):
            errs.append(f"sobra en disco: {extra}")
        for e in errs:
            print("ERROR:", e)
        print("--check:", "FALLA" if errs else "OK")
        return 1 if errs else 0
    out.mkdir(parents=True, exist_ok=True)
    for p in out.glob("[0-9][0-9]-*.md"):
        p.unlink()
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    for e in errs:
        print("AVISO:", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
