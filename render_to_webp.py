#!/usr/bin/env python3
"""
Render Markdown & code files ➜ PDF ➜ WebP pages and/or tiles (with optional hashing),
and write a tile manifest.

Defaults:
- Emits BOTH pages and tiles
- Computes SHA-256 for each tile
- Tile manifest format: JSONL (one JSON object per tile)

Examples:
  python render_to_webp.py --input-dir ./docs --out-dir ./out
  python render_to_webp.py --input-dir ./docs --out-dir ./out --emit tiles --no-hash-tiles --manifest json
"""

import argparse
import html
import json
import os
import pathlib
import re
import shutil
import sys
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

# HTML ➜ PDF
from weasyprint import HTML

# Markdown + syntax highlight
import markdown as md
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename, TextLexer

# PDF ➜ WebP
import fitz  # PyMuPDF
from PIL import Image


SUPPORTED_MD = {".md", ".markdown", ".mdx"}
SUPPORTED_CODE = {
    ".js", ".ts", ".tsx", ".jsx",
    ".py", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp", ".cs",
    ".sh", ".bash", ".zsh",
    ".json", ".yml", ".yaml", ".toml",
    ".html", ".css"
}
DEFAULT_PYGMENTS_STYLE = "friendly"  # high-contrast light theme


@dataclass
class RenderConfig:
    page_width_px: int = 1200
    body_font_size: int = 15
    code_font_size: int = 14
    line_height: float = 1.45
    font_family_mono: str = "JetBrains Mono, Menlo, Consolas, Monaco, 'Courier New', monospace"
    font_family_sans: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Ubuntu, 'Helvetica Neue', Arial, sans-serif"
    pygments_style: str = DEFAULT_PYGMENTS_STYLE
    extra_css_path: Optional[str] = None
    dpi: int = 200
    webp_quality: int = 90
    webp_lossless: bool = False
    tile_size: int = 1024
    tile_overlap: float = 0.10
    emit: str = "both"  # pages | tiles | both
    manifest: str = "jsonl"  # jsonl | json | tsv | none
    hash_tiles: bool = True
    # runtime
    input_dir: pathlib.Path = pathlib.Path(".")


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def md_to_html(markdown_text: str, cfg: RenderConfig, title: str) -> str:
    """Markdown -> HTML using Python-Markdown + CodeHilite."""
    extensions = [
        "fenced_code", "codehilite", "tables", "toc", "sane_lists", "attr_list",
    ]
    extension_configs = {
        "codehilite": {
            "guess_lang": False,
            "pygments_style": cfg.pygments_style,
            "noclasses": False,  # use CSS classes (global stylesheet)
        }
    }
    html_body = md.markdown(markdown_text, extensions=extensions, extension_configs=extension_configs)
    return wrap_html(html_body, cfg, title)


def code_to_html(code_text: str, filename: str, cfg: RenderConfig, title: str) -> str:
    """Single code file -> HTML via Pygments."""
    try:
        lexer = guess_lexer_for_filename(filename, code_text)
    except Exception:
        lexer = TextLexer()
    formatter = HtmlFormatter(style=cfg.pygments_style, linenos=True, nowrap=False, cssclass="codehilite")
    highlighted = highlight(code_text, lexer, formatter)
    body = f"<article class='code-article'>{highlighted}</article>"
    return wrap_html(body, cfg, title, extra_css=formatter.get_style_defs('.codehilite'))


def wrap_html(body: str, cfg: RenderConfig, title: str, extra_css: Optional[str] = None) -> str:
    """Wrap body with minimal HTML + embedded CSS tailored for print/PDF."""
    base_css = f"""
    @page {{
      size: A4;
      margin: 24px;
    }}

    :root {{
      --page-width: {cfg.page_width_px}px;
      --body-font-size: {cfg.body_font_size}px;
      --code-font-size: {cfg.code_font_size}px;
      --line-height: {cfg.line_height};
      --mono: {cfg.font_family_mono};
      --sans: {cfg.font_family_sans};
    }}

    html, body {{
      background: #fff;
      color: #111;
      font-family: var(--sans);
      font-size: var(--body-font-size);
      line-height: var(--line-height);
    }}

    main {{
      width: var(--page-width);
      margin: 0 auto;
      padding: 8px 0 24px 0;
    }}

    h1, h2, h3, h4, h5 {{
      font-weight: 700;
      line-height: 1.25;
      margin: 1.2em 0 0.5em;
    }}

    h1 {{ font-size: calc(var(--body-font-size) * 1.8); }}
    h2 {{ font-size: calc(var(--body-font-size) * 1.5); }}
    h3 {{ font-size: calc(var(--body-font-size) * 1.25); }}

    p, li {{ margin: 0.4em 0; }}

    code, pre, .codehilite {{
      font-family: var(--mono);
      font-feature-settings: "liga" 0; /* disable ligatures for code correctness */
      font-size: var(--code-font-size);
    }}

    pre {{
      background: #fbfbfc;
      border: 1px solid #e6e6e9;
      border-radius: 8px;
      padding: 12px 14px;
      overflow: auto;
    }}

    .codehilite .linenos {{ color: #999; }}

    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #e6e6e9; padding: 6px 8px; vertical-align: top; }}

    blockquote {{
      border-left: 4px solid #e6e6e9;
      margin: 0.8em 0;
      padding: 0.2em 1em;
      color: #333;
      background: #fafafa;
    }}

    header.doc-header {{
      font-size: 0.9em;
      color: #555;
      border-bottom: 1px solid #eee;
      margin-bottom: 12px;
      padding-bottom: 6px;
    }}
    """

    pyg_css = HtmlFormatter(style=cfg.pygments_style).get_style_defs('.codehilite')
    extra = extra_css or ""
    user_css = ""
    if cfg.extra_css_path and os.path.exists(cfg.extra_css_path):
        user_css = pathlib.Path(cfg.extra_css_path).read_text(encoding="utf-8", errors="ignore")

    head = f"""
    <head>
      <meta charset="utf-8" />
      <title>{html.escape(title)}</title>
      <style>{base_css}\n{pyg_css}\n{extra}\n{user_css}</style>
    </head>
    """

    container = f"""
    <header class="doc-header">{html.escape(title)}</header>
    <main>{body}</main>
    """
    return f"<!doctype html><html>{head}<body>{container}</body></html>"


def html_to_pdf(html_str: str, pdf_path: pathlib.Path) -> None:
    HTML(string=html_str, base_url=str(pdf_path.parent)).write_pdf(str(pdf_path))


def pdf_to_webp_pages(pdf_path: pathlib.Path, out_dir: pathlib.Path, dpi: int, quality: int, lossless: bool) -> List[pathlib.Path]:
    """Rasterize each PDF page to WebP; return list of paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    scale = dpi / 72.0
    webps = []
    for i, page in enumerate(doc):
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_path = out_dir / f"{pdf_path.stem}-p{i+1:03}.webp"
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if lossless:
            img.save(out_path, "WEBP", lossless=True, method=6)
        else:
            img.save(out_path, "WEBP", quality=quality, method=6)
        webps.append(out_path)
    doc.close()
    return webps


def tile_webp(webp_path: pathlib.Path, tile_size: int, overlap: float, quality: int, lossless: bool) -> List[Tuple[pathlib.Path, Tuple[int,int,int,int]]]:
    """Tile a WebP into NxN tiles; return list of (tile_path, bbox)."""
    im = Image.open(webp_path).convert("RGB")
    W, H = im.size
    step = max(1, int(tile_size * (1.0 - overlap)))
    tiles = []
    for y in range(0, max(H - tile_size, 0) + 1, step):
        for x in range(0, max(W - tile_size, 0) + 1, step):
            crop = im.crop((x, y, x + tile_size, y + tile_size))
            out = webp_path.with_name(f"{webp_path.stem}-x{x}-y{y}.webp")
            if lossless:
                crop.save(out, "WEBP", lossless=True, method=6)
            else:
                crop.save(out, "WEBP", quality=quality, method=6)
            tiles.append((out, (x, y, x + tile_size, y + tile_size)))
    return tiles


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_title(path: pathlib.Path) -> str:
    return path.name


def render_file(src_path: pathlib.Path, out_root: pathlib.Path, cfg: RenderConfig) -> None:
    rel = src_path.relative_to(cfg.input_dir)
    doc_id = rel.as_posix().replace("/", "__")
    dest_dir = out_root / doc_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    title = sanitize_title(src_path)
    ext = src_path.suffix.lower()

    # 1) Build HTML
    if ext in SUPPORTED_MD:
        html_str = md_to_html(read_text(src_path), cfg, title)
    else:
        code_text = read_text(src_path)
        html_str = code_to_html(code_text, src_path.name, cfg, title)

    # 2) HTML ➜ PDF
    pdf_path = dest_dir / f"{src_path.stem}.pdf"
    html_to_pdf(html_str, pdf_path)

    # 3) PDF ➜ WebP pages (always render pages internally; we'll drop them later if emit=tiles)
    pages_dir = dest_dir / "pages"
    pages_dir.mkdir(exist_ok=True, parents=True)
    webps = pdf_to_webp_pages(pdf_path, pages_dir, cfg.dpi, cfg.webp_quality, cfg.webp_lossless)

    # If emitting pages, write a simple list for convenience
    if cfg.emit in ("pages", "both"):
        (pages_dir / "pages.txt").write_text("\n".join([p.name for p in webps]), encoding="utf-8")

    # 4) Tiles + manifest (if requested)
    if cfg.emit in ("tiles", "both"):
        tiles_dir = dest_dir / "tiles"
        tiles_dir.mkdir(exist_ok=True, parents=True)

        records = []
        tile_counter = 0
        for wp in webps:
            tiles = tile_webp(wp, cfg.tile_size, cfg.tile_overlap, cfg.webp_quality, cfg.webp_lossless)
            # extract page number if present like "-p001"
            m = re.search(r"-p(\d+)$", wp.stem)
            page_num = int(m.group(1)) if m else 1
            for tile_path, bbox in tiles:
                final_tile = tiles_dir / tile_path.name
                tile_path.replace(final_tile)
                rec = {
                    "doc_id": doc_id,
                    "page": page_num,
                    "tile_idx": tile_counter,
                    "tile_path": str(final_tile),
                    "page_path": str(wp),
                    "bbox": {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                    "tile_px": cfg.tile_size,
                    "overlap": cfg.tile_overlap,
                    "source_pdf": str(pdf_path),
                    "source_file": str(src_path),
                }
                if cfg.hash_tiles:
                    rec["sha256"] = sha256_file(final_tile)
                records.append(rec)
                tile_counter += 1

        # Write manifest
        if cfg.manifest != "none":
            if cfg.manifest == "jsonl":
                outp = tiles_dir / "tiles.jsonl"
                with open(outp, "w", encoding="utf-8") as f:
                    for r in records:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
            elif cfg.manifest == "json":
                (tiles_dir / "tiles.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
            elif cfg.manifest == "tsv":
                lines = [
                    f"{pathlib.Path(r['tile_path']).name}\tpage={pathlib.Path(r['page_path']).name}\t"
                    f"bbox=({r['bbox']['x0']}, {r['bbox']['y0']}, {r['bbox']['x1']}, {r['bbox']['y1']})"
                    + (f"\tsha256={r['sha256']}" if "sha256" in r else "")
                    for r in records
                ]
                (tiles_dir / "tiles.tsv").write_text("\n".join(lines), encoding="utf-8")

    # 5) If emit=tiles only, remove the pages directory to keep output lean
    if cfg.emit == "tiles":
        try:
            shutil.rmtree(pages_dir)
        except Exception:
            pass


def discover_sources(root: pathlib.Path) -> List[pathlib.Path]:
    paths = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in SUPPORTED_MD or ext in SUPPORTED_CODE:
            paths.append(p)
    return paths


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Render Markdown & code ➜ PDF ➜ WebP pages/tiles (with hashing & manifest).")
    ap.add_argument("--input-dir", required=True, type=pathlib.Path, help="Directory containing .md and/or code files.")
    ap.add_argument("--out-dir", required=True, type=pathlib.Path, help="Output directory to write PDFs/WebPs.")
    ap.add_argument("--page-width-px", type=int, default=1200)
    ap.add_argument("--body-font-size", type=int, default=15)
    ap.add_argument("--code-font-size", type=int, default=14)
    ap.add_argument("--line-height", type=float, default=1.45)
    ap.add_argument("--pygments-style", type=str, default=DEFAULT_PYGMENTS_STYLE)
    ap.add_argument("--extra-css-path", type=str, default=None, help="Optional path to extra CSS to inject.")
    ap.add_argument("--dpi", type=int, default=200, help="Rasterization DPI for PDF➜image (200–220 is a good start).")
    ap.add_argument("--webp-quality", type=int, default=90, help="Ignored if --webp-lossless is set.")
    ap.add_argument("--webp-lossless", action="store_true", help="Encode WebP losslessly (larger files).")
    ap.add_argument("--tile-size", type=int, default=1024, help="Tile edge length in pixels.")
    ap.add_argument("--tile-overlap", type=float, default=0.10, help="Fractional overlap between tiles (0.0–0.5).")
    ap.add_argument("--emit", choices=["pages", "tiles", "both"], default="both",
                    help="What to emit to disk (default: both).")
    ap.add_argument("--manifest", choices=["jsonl", "json", "tsv", "none"], default="jsonl",
                    help="Tile manifest format (default: jsonl).")
    ap.add_argument("--no-hash-tiles", action="store_true",
                    help="Disable computing SHA-256 for each tile (enabled by default).")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = RenderConfig(
        page_width_px=args.page_width_px,
        body_font_size=args.body_font_size,
        code_font_size=args.code_font_size,
        line_height=args.line_height,
        pygments_style=args.pygments_style,
        extra_css_path=args.extra_css_path,
        dpi=args.dpi,
        webp_quality=args.webp_quality,
        webp_lossless=args.webp_lossless,
        tile_size=args.tile_size,
        tile_overlap=args.tile_overlap,
        emit=args.emit,
        manifest=args.manifest,
        hash_tiles=not args.no_hash_tiles,
        input_dir=args.input_dir,
    )

    sources = discover_sources(args.input_dir)
    if not sources:
        print("No supported files found.", file=sys.stderr)
        sys.exit(1)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for src in sources:
        print(f"[render] {src}")
        render_file(src, args.out_dir, cfg)

    print(f"\nDone. Output written to: {args.out_dir.resolve()}\n")


if __name__ == "__main__":
    main()
