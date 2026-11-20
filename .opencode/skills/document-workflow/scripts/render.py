#!/usr/bin/env python3
"""Render approved Markdown/CSV sources into local deliverables.

No third-party packages are used by the host interpreter. PDF and XLSX jobs
re-exec with the dedicated venv under ~/.local/state/document-workflow/.
"""
import argparse
import csv
import hashlib
import html as html_mod
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = pathlib.Path.home() / ".local/state/document-workflow"
PANDOC = STATE / "bin/pandoc"
VENV_PY = STATE / "venv/bin/python"
TOOL_VERSION = {
    "docx": "pandoc 3.14",
    "pdf": "pandoc 3.14 + reportlab 5.1.0",
    "csv": "python csv stdlib",
    "xlsx": "openpyxl 3.1.5",
}
FORMATS = tuple(TOOL_VERSION)


class RenderError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def fail(message, code=1):
    raise RenderError(message, code)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                value = value.strip().strip('"').strip("'")
                meta[key.strip()] = value
    return meta, text


def project_delivery_dir(source):
    docs = pathlib.Path.home() / "Documentos"
    for parent in source.parents:
        if (parent / ".git").exists():
            return parent / "entregables"
    if docs in source.parents or source.parent == docs:
        node = source.parent if source.parent == docs else source.parent
        while node.parent != docs and node != docs:
            node = node.parent
        return (node if node != docs else docs) / "entregables"
    return docs / "entregables" / source.parent.name


def safe_stem(value):
    stem = re.sub(r"[^A-Za-z0-9À-ÿ_-]+", "-", str(value or "")).strip("-")
    return stem or "entregable"


def resolve_output(source, meta, fmt, explicit, force):
    directory = project_delivery_dir(source)
    name = safe_stem(meta.get("title") or source.stem)
    if explicit:
        target = pathlib.Path(explicit).expanduser().resolve()
        try:
            target.relative_to(directory.resolve())
        except ValueError:
            fail(f"explicit output must stay inside {directory}", 3)
    else:
        target = directory / f"{name}.{fmt}"
    if target.exists() and not force:
        fail(f"output already exists: {target} (use --force only with confirmation)", 3)
    return target


def pandoc_args(meta, defaults, output, source):
    args = [str(PANDOC), "--defaults", str(ROOT / "defaults" / defaults)]
    for key in ("title", "author", "date", "lang"):
        if meta.get(key):
            args += ["--metadata", f"{key}={meta[key]}"]
    args += ["-o", str(output), str(source)]
    return args


def check_tools(fmt):
    if not PANDOC.is_file():
        fail(f"Pandoc is not installed at {PANDOC}; run scripts/install.sh")
    if fmt in ("pdf", "xlsx") and not VENV_PY.is_file():
        fail(f"venv interpreter is missing at {VENV_PY}")


def render_docx(source, meta, output):
    check_tools("docx")
    subprocess.run(pandoc_args(meta, "docx.yaml", output, source),
                   check=True, capture_output=True, text=True)


def pandoc_html(source, meta):
    check_tools("pdf")
    with tempfile.TemporaryDirectory(prefix="document-workflow-") as tmp:
        target = pathlib.Path(tmp) / "document.html"
        subprocess.run(pandoc_args(meta, "html.yaml", target, source),
                       check=True, capture_output=True, text=True)
        return target.read_text(encoding="utf-8")


def clean_text(parts):
    value = html_mod.unescape("".join(parts))
    return re.sub(r"\s+", " ", value).strip()


class HtmlToFlowables(HTMLParser):
    """Convert the constrained HTML5 emitted by Pandoc into ReportLab flowables."""

    HEADINGS = {"h1": "Heading1", "h2": "Heading2", "h3": "Heading3"}

    def __init__(self, styles):
        super().__init__(convert_charrefs=True)
        self.styles = styles
        self.story = []
        self.skip = 0
        self.current = None
        self.buffer = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag in ("head", "style", "script"):
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag in (*self.HEADINGS, "p", "li"):
            self.current = tag
            self.buffer = []

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif self.current:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag in ("head", "style", "script"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        from reportlab.lib import colors
        from reportlab.platypus import Paragraph, Table, TableStyle

        if tag in ("td", "th") and self.cell is not None:
            self.row.append(clean_text(self.cell))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            rows = [[Paragraph(escape_xml(cell), self.styles["BodyText"])
                     for cell in row] for row in self.table]
            if rows:
                table = Table(rows, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#888888")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                self.story.append(table)
            self.table = None
        elif tag == "li" and self.current == "li":
            text = escape_xml(clean_text(self.buffer))
            if text:
                self.story.append(Paragraph(f"• {text}", self.styles["BodyText"]))
            self.current = None
        elif tag in (*self.HEADINGS, "p") and self.current == tag:
            text = escape_xml(clean_text(self.buffer))
            if text:
                style = self.styles[self.HEADINGS.get(tag, "BodyText")]
                self.story.append(Paragraph(text, style))
            self.current = None

    def result(self):
        return self.story


def escape_xml(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))


def render_pdf(source, meta, output):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    parser = HtmlToFlowables(getSampleStyleSheet())
    parser.feed(pandoc_html(source, meta))
    story = parser.result() or [Paragraph("", getSampleStyleSheet()["BodyText"])]
    doc = SimpleDocTemplate(str(output), pagesize=A4,
                            title=meta.get("title") or source.stem,
                            author=meta.get("author", ""))
    doc.build(story)


def load_table(source):
    if source.suffix.lower() == ".csv":
        with open(source, "r", encoding="utf-8", newline="") as handle:
            return [row for row in csv.reader(handle) if row]
    meta, text = parse_frontmatter(source)
    del meta
    rows = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        fail("no pipe table found in Markdown source; CSV output needs a table")
    return rows


def render_csv(source, meta, output):
    del meta
    rows = load_table(source)
    with open(output, "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)


def render_xlsx(source, meta, output):
    from openpyxl import Workbook

    del meta
    rows = load_table(source)
    book = Workbook()
    sheet = book.active
    sheet.title = "datos"
    for row in rows:
        sheet.append(row)
    book.save(output)


def validate_output(output, fmt):
    if not output.is_file() or output.stat().st_size == 0:
        fail(f"empty or missing output: {output}")
    head = output.read_bytes()[:4]
    if fmt in ("docx", "xlsx") and not head.startswith(b"PK\x03\x04"):
        fail(f"output does not look like a {fmt} package: {output}")
    if fmt == "pdf" and not head.startswith(b"%PDF"):
        fail(f"output does not look like PDF: {output}")
    if fmt == "csv":
        with open(output, "r", encoding="utf-8", newline="") as handle:
            if not next(csv.reader(handle), None):
                fail(f"CSV has no rows: {output}")


def write_provenance(output, source, sha, fmt, meta):
    payload = {
        "source": str(source),
        "source_sha256": sha,
        "output": output.name,
        "format": fmt,
        "tool": TOOL_VERSION[fmt],
        "title": meta.get("title", ""),
        "template": meta.get("template", ""),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    target = pathlib.Path(str(output) + ".provenance.json")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--format", required=True, choices=FORMATS)
    parser.add_argument("--title")
    parser.add_argument("--author")
    parser.add_argument("--date")
    parser.add_argument("--lang")
    parser.add_argument("--template")
    parser.add_argument("--output")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.format in ("pdf", "xlsx") and not os.environ.get("DOCUMENT_WORKFLOW_VENV"):
        if not VENV_PY.is_file():
            fail(f"venv interpreter is missing at {VENV_PY}")
        env = os.environ.copy()
        env["DOCUMENT_WORKFLOW_VENV"] = "1"
        os.execve(str(VENV_PY), [str(VENV_PY), str(pathlib.Path(__file__).resolve()),
                                 *sys.argv[1:]], env)

    source = pathlib.Path(args.source).expanduser().resolve()
    if not source.is_file():
        fail(f"source not found: {source}")
    meta, _ = parse_frontmatter(source) if source.suffix.lower() == ".md" else ({}, "")
    for key in ("title", "author", "date", "lang", "template"):
        value = getattr(args, key)
        if value:
            meta[key] = value
    meta.setdefault("lang", "es")
    if args.format in ("docx", "pdf") and not meta.get("title"):
        meta["title"] = source.stem

    check_tools(args.format)
    before = sha256(source)
    output = resolve_output(source, meta, args.format, args.output, args.force)
    output.parent.mkdir(parents=True, exist_ok=True)

    renderers = {
        "docx": render_docx,
        "pdf": render_pdf,
        "csv": render_csv,
        "xlsx": render_xlsx,
    }
    renderers[args.format](source, meta, output)

    if sha256(source) != before:
        fail(f"source changed during render: {source}")
    validate_output(output, args.format)
    write_provenance(output, source, before, args.format, meta)
    print(json.dumps({
        "output": str(output),
        "format": args.format,
        "tool": TOOL_VERSION[args.format],
        "bytes": output.stat().st_size,
        "source_sha256": before,
        "provenance": str(output) + ".provenance.json",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RenderError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(exc.code)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        message = detail[-1] if detail else f"subprocess exit {exc.returncode}"
        print(json.dumps({"error": message}), file=sys.stderr)
        sys.exit(1)
