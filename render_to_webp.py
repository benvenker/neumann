#!/usr/bin/env python3
"""
Render Markdown & code files ➜ PDF ➜ WebP pages and/or tiles (with hashing & manifest),
with tight CSS and a 'bands' tiler for full-width horizontal tiles.

Defaults:
- Emits pages only (no tiles)
- No manifest generated (use --manifest jsonl/json/tsv to enable)
- Tiling mode: 'bands' (full-width horizontal slices, when tiles are enabled)
- Line numbers: 'inline' for code files (no wide gutter)

Examples:
  python render_to_webp.py --input-dir ./docs --out-dir ./out
  python render_to_webp.py --input-dir ./docs --out-dir ./out --emit both --manifest jsonl
  python render_to_webp.py --input-dir ./docs --out-dir ./out --tile-mode bands --band-height 1100
"""

import argparse
import html
import json
import os
import pathlib
import re
import shutil
import sys
from dataclasses import dataclass
from typing import Any, Literal

# PDF ➜ WebP
import fitz  # PyMuPDF

# Markdown + syntax highlight
import markdown as md
from PIL import Image
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, guess_lexer_for_filename

# HTML ➜ PDF
from weasyprint import HTML

from config import config as app_config
from ids import make_doc_id
from utils.hash_utils import sha256_file

SUPPORTED_MD = {".md", ".markdown", ".mdx"}
SUPPORTED_CODE = {
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".sh",
    ".bash",
    ".zsh",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".html",
    ".css",
}
DEFAULT_PYGMENTS_STYLE = "friendly"  # high-contrast light theme


@dataclass
class RenderConfig:
    page_width_px: int = 1200
    page_margin_px: int = 12  # tighter default
    body_font_size: int = 15
    code_font_size: int = 14
    line_height: float = 1.4
    font_family_mono: str = "JetBrains Mono, Menlo, Consolas, Monaco, 'Courier New', monospace"
    font_family_sans: str = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Ubuntu, 'Helvetica Neue', Arial, sans-serif"
    )
    pygments_style: str = DEFAULT_PYGMENTS_STYLE
    extra_css_path: str | None = None
    show_header: bool = False  # hide the header bar by default
    tight: bool = True  # compact paddings/borders

    dpi: int = 200
    webp_quality: int = 90
    webp_lossless: bool = False

    emit: str = "pages"  # pages | tiles | both
    manifest: str = "none"  # jsonl | json | tsv | none
    hash_tiles: bool = True

    tile_mode: str = "bands"  # bands | grid
    tile_size: int = 1024  # for grid mode (square tiles)
    tile_overlap: float = 0.10  # for both modes
    band_height: int = 1100  # for bands mode (full width, fixed height)

    linenos: str = "inline"  # inline | table | none  (code files only)
    input_dir: pathlib.Path = pathlib.Path(".")
    asset_root: str = "out"  # root path segment for asset URIs


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def md_to_html(markdown_text: str, cfg: RenderConfig, title: str) -> str:
    """Markdown -> HTML. For Markdown code blocks we avoid table-style linenos to keep things tight."""
    extensions = [
        "fenced_code",
        "codehilite",
        "tables",
        "toc",
        "sane_lists",
        "attr_list",
    ]
    # CodeHilite's 'linenums' is bool only; using table numbers makes a wide gutter.
    linenums_bool = cfg.linenos == "table"
    extension_configs = {
        "codehilite": {
            "guess_lang": False,
            "pygments_style": cfg.pygments_style,
            "noclasses": False,
            "linenums": linenums_bool,
        }
    }
    html_body = md.markdown(markdown_text, extensions=extensions, extension_configs=extension_configs)
    return wrap_html(html_body, cfg, title)


def code_to_html(code_text: str, filename: str, cfg: RenderConfig, title: str) -> str:
    """Single code file -> HTML via Pygments, with controllable line-number mode."""
    try:
        lexer = guess_lexer_for_filename(filename, code_text)
    except Exception:
        lexer = TextLexer()
    # Map lineno mode
    ln: bool | Literal["inline"] = False
    if cfg.linenos == "table":
        ln = True
    elif cfg.linenos == "inline":
        ln = "inline"
    formatter = HtmlFormatter(style=cfg.pygments_style, linenos=ln, nowrap=False, cssclass="codehilite")
    highlighted = highlight(code_text, lexer, formatter)
    body = f"<article class='code-article'>{highlighted}</article>"
    return wrap_html(body, cfg, title, extra_css=formatter.get_style_defs(".codehilite"))


def wrap_html(body: str, cfg: RenderConfig, title: str, extra_css: str | None = None) -> str:
    """Wrap body with compact HTML+CSS for print/PDF."""
    pre_pad = 8 if cfg.tight else 12
    pre_bg = "#fff" if cfg.tight else "#fbfbfc"
    pre_border = "1px solid #eee" if cfg.tight else "1px solid #e6e6e9"
    header_display = "block" if cfg.show_header else "none"

    base_css = f"""
    @page {{
      size: A4;
      margin: {cfg.page_margin_px}px;
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
      padding: 0;
    }}

    h1, h2, h3, h4, h5 {{
      font-weight: 700;
      line-height: 1.23;
      margin: 0.9em 0 0.45em;
    }}

    h1 {{ font-size: calc(var(--body-font-size) * 1.7); }}
    h2 {{ font-size: calc(var(--body-font-size) * 1.45); }}
    h3 {{ font-size: calc(var(--body-font-size) * 1.2); }}

    p, li {{ margin: 0.3em 0; }}

    code, pre, .codehilite {{
      font-family: var(--mono);
      font-feature-settings: "liga" 0;
      font-size: var(--code-font-size);
    }}

    pre {{
      background: {pre_bg};
      border: {pre_border};
      border-radius: 6px;
      padding: {pre_pad}px {pre_pad + 2}px;
      overflow: auto;
      margin: 0.6em 0;
    }}

    /* Pygments line-number tweaks */
    .codehilite table {{ border-spacing: 0; width: 100%; }}
    .codehilite td.linenos {{
      width: 2.0em;
      color: #a7a7a7;
      padding: 0 4px 0 2px;
    }}
    .codehilite td.code {{ padding-left: 6px; }}

    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #eee; padding: 4px 6px; vertical-align: top; }}

    blockquote {{
      border-left: 3px solid #e6e6e6;
      margin: 0.6em 0;
      padding: 0.2em 0.8em;
      color: #333;
      background: #fafafa;
    }}

    header.doc-header {{
      display: {header_display};
      font-size: 0.9em;
      color: #555;
      border-bottom: 1px solid #eee;
      margin: 0 0 8px 0;
      padding: 4px 0;
    }}
    """

    pyg_css = HtmlFormatter(style=cfg.pygments_style).get_style_defs(".codehilite")
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


def pdf_to_webp_pages(
    pdf_path: pathlib.Path, out_dir: pathlib.Path, dpi: int, quality: int, lossless: bool
) -> list[pathlib.Path]:
    """Rasterize each PDF page to WebP; return list of paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    webps = []
    with fitz.open(str(pdf_path)) as doc:
        scale = dpi / 72.0
        for i, page in enumerate(doc):
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out_path = out_dir / f"{pdf_path.stem}-p{i + 1:03}.webp"
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if lossless:
                img.save(out_path, "WEBP", lossless=True, method=6)
            else:
                img.save(out_path, "WEBP", quality=quality, method=6)
            webps.append(out_path)
    return webps


def tile_grid(
    webp_path: pathlib.Path, tile_size: int, overlap: float, quality: int, lossless: bool
) -> list[tuple[pathlib.Path, tuple[int, int, int, int]]]:
    """Square grid tiling with guaranteed edge coverage."""
    with Image.open(webp_path) as im:
        im = im.convert("RGB")
        W, H = im.size
        step = max(1, int(tile_size * (1.0 - overlap)))

        # Generate x coordinates ensuring right edge is covered
        x_coords = []
        x = 0
        while x < W:
            if x + tile_size >= W:
                # Ensure last tile covers right edge
                x_coords.append(max(0, W - tile_size))
                break
            x_coords.append(x)
            x += step

        # Generate y coordinates ensuring bottom edge is covered
        y_coords = []
        y = 0
        while y < H:
            if y + tile_size >= H:
                # Ensure last tile covers bottom edge
                y_coords.append(max(0, H - tile_size))
                break
            y_coords.append(y)
            y += step

        tiles = []
        for y in y_coords:
            for x in x_coords:
                # Clamp crop coordinates to image bounds
                x0, y0 = x, y
                x1 = min(x + tile_size, W)
                y1 = min(y + tile_size, H)
                crop = im.crop((x0, y0, x1, y1))
                out = webp_path.with_name(f"{webp_path.stem}-x{x}-y{y}.webp")
                if lossless:
                    crop.save(out, "WEBP", lossless=True, method=6)
                else:
                    crop.save(out, "WEBP", quality=quality, method=6)
                tiles.append((out, (x0, y0, x1, y1)))
    return tiles


def tile_bands(
    webp_path: pathlib.Path, band_height: int, overlap: float, quality: int, lossless: bool
) -> list[tuple[pathlib.Path, tuple[int, int, int, int]]]:
    """Full-width horizontal slices with vertical overlap."""
    with Image.open(webp_path) as im:
        im = im.convert("RGB")
        W, H = im.size
        step = max(1, int(band_height * (1.0 - overlap)))
        tiles = []
        y = 0
        while True:
            y_end = min(y + band_height, H)
            crop = im.crop((0, y, W, y_end))
            out = webp_path.with_name(f"{webp_path.stem}-y{y}.webp")
            if lossless:
                crop.save(out, "WEBP", lossless=True, method=6)
            else:
                crop.save(out, "WEBP", quality=quality, method=6)
            tiles.append((out, (0, y, W, y_end)))
            if y_end >= H:
                break
            y += step
    return tiles


def sanitize_title(path: pathlib.Path) -> str:
    return path.name


def render_file(src_path: pathlib.Path, out_root: pathlib.Path, cfg: RenderConfig) -> None:
    doc_id = make_doc_id(src_path, cfg.input_dir)
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

    # 3) PDF ➜ WebP pages
    pages_dir = dest_dir / "pages"
    pages_dir.mkdir(exist_ok=True, parents=True)
    webps = pdf_to_webp_pages(pdf_path, pages_dir, cfg.dpi, cfg.webp_quality, cfg.webp_lossless)

    # Save a quick list of pages if keeping pages
    if cfg.emit in ("pages", "both"):
        (pages_dir / "pages.txt").write_text("\n".join([p.name for p in webps]), encoding="utf-8")

    # Always emit pages.jsonl manifest in pages directory
    # Fields: doc_id, page, uri, sha256, bytes, width, height, source_pdf, source_file
    pages_records: list[dict[str, Any]] = []
    for wp in webps:
        m = re.search(r"-p(\d+)$", wp.stem)
        page_num = int(m.group(1)) if m else 1
        # Compute metadata
        with Image.open(wp) as im:
            width, height = im.size
        file_bytes = wp.stat().st_size
        sha = sha256_file(wp)
        # Build HTTP URI using ASSET_BASE_URL and asset_root
        # Output structure: <out_root>/<doc_id>/pages/<filename>
        uri = f"{app_config.ASSET_BASE_URL}/{cfg.asset_root}/{doc_id}/pages/{wp.name}"
        pages_records.append(
            {
                "doc_id": doc_id,
                "page": page_num,
                "uri": uri,
                "sha256": sha,
                "bytes": file_bytes,
                "width": width,
                "height": height,
                "source_pdf": str(pdf_path),
                "source_file": str(src_path),
            }
        )
    with open(pages_dir / "pages.jsonl", "w", encoding="utf-8") as f:
        for rec in pages_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 4) Tiles + manifest
    if cfg.emit in ("tiles", "both"):
        tiles_dir = dest_dir / "tiles"
        tiles_dir.mkdir(exist_ok=True, parents=True)

        records: list[dict[str, Any]] = []
        tile_counter = 0
        for wp in webps:
            # page number like "-p001"
            m = re.search(r"-p(\d+)$", wp.stem)
            page_num = int(m.group(1)) if m else 1

            if cfg.tile_mode == "grid":
                tiles = tile_grid(wp, cfg.tile_size, cfg.tile_overlap, cfg.webp_quality, cfg.webp_lossless)
            else:
                tiles = tile_bands(wp, cfg.band_height, cfg.tile_overlap, cfg.webp_quality, cfg.webp_lossless)

            for tile_path, bbox in tiles:
                final_tile = tiles_dir / tile_path.name
                tile_path.replace(final_tile)
                rec = {
                    "doc_id": doc_id,
                    "page": page_num,
                    "tile_idx": tile_counter,
                    "tile_path": str(final_tile),
                    "page_path": str(wp) if cfg.emit in ("pages", "both") else None,
                    "bbox": {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                    "tile_mode": cfg.tile_mode,
                    "tile_px": cfg.tile_size if cfg.tile_mode == "grid" else None,
                    "band_height": cfg.band_height if cfg.tile_mode == "bands" else None,
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
                    f"{pathlib.Path(r['tile_path']).name}\tpage={pathlib.Path(r['page_path']).name if r['page_path'] else 'None'}\t"
                    f"bbox=({r['bbox']['x0']}, {r['bbox']['y0']}, {r['bbox']['x1']}, {r['bbox']['y1']})"
                    + (f"\tsha256={r['sha256']}" if "sha256" in r else "")
                    for r in records
                ]
                (tiles_dir / "tiles.tsv").write_text("\n".join(lines), encoding="utf-8")

    # 5) If emit=tiles only, remove pages to keep output lean
    if cfg.emit == "tiles":
        import contextlib

        with contextlib.suppress(Exception):
            shutil.rmtree(pages_dir)


def discover_sources(root: pathlib.Path) -> list[pathlib.Path]:
    paths = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in SUPPORTED_MD or ext in SUPPORTED_CODE:
            paths.append(p)
    return paths


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Render Markdown & code ➜ PDF ➜ WebP (tight CSS, bands/grid tiling, hashing, manifest)."
    )
    ap.add_argument("--input-dir", required=True, type=pathlib.Path, help="Directory containing .md and/or code files.")
    ap.add_argument("--out-dir", required=True, type=pathlib.Path, help="Output directory to write PDFs/WebPs.")
    ap.add_argument("--asset-root", type=str, default="out", help="Root path segment for asset URIs (default: 'out').")

    # layout & style
    ap.add_argument("--page-width-px", type=int, default=1200)
    ap.add_argument("--page-margin-px", type=int, default=12)
    ap.add_argument("--body-font-size", type=int, default=15)
    ap.add_argument("--code-font-size", type=int, default=14)
    ap.add_argument("--line-height", type=float, default=1.4)
    ap.add_argument("--pygments-style", type=str, default=DEFAULT_PYGMENTS_STYLE)
    ap.add_argument("--extra-css-path", type=str, default=None, help="Optional path to extra CSS to inject.")
    ap.add_argument("--show-header", action="store_true", help="Show a small header with the file name.")
    ap.add_argument(
        "--loose", action="store_true", help="Use roomier paddings/borders (opposite of --loose is the tight default)."
    )
    ap.add_argument(
        "--linenos",
        choices=["inline", "table", "none"],
        default="inline",
        help="Line-number style for code files (default: inline).",
    )

    # raster/encode
    ap.add_argument("--dpi", type=int, default=200, help="Rasterization DPI for PDF➜image (200–220 is a good start).")
    ap.add_argument("--webp-quality", type=int, default=90, help="Ignored if --webp-lossless is set.")
    ap.add_argument("--webp-lossless", action="store_true", help="Encode WebP losslessly (larger files).")

    # outputs
    ap.add_argument("--emit", choices=["pages", "tiles", "both"], default="pages", help="What to emit to disk.")
    ap.add_argument(
        "--manifest", choices=["jsonl", "json", "tsv", "none"], default="none", help="Tile manifest format."
    )
    ap.add_argument("--no-hash-tiles", action="store_true", help="Disable SHA-256 for each tile (enabled by default).")

    # tiling
    ap.add_argument(
        "--tile-mode", choices=["bands", "grid"], default="bands", help="bands = full-width rows; grid = square tiles."
    )
    ap.add_argument("--tile-size", type=int, default=1024, help="Square tile size for grid mode.")
    ap.add_argument("--tile-overlap", type=float, default=0.10, help="Fractional overlap (0.0–0.5).")
    ap.add_argument("--band-height", type=int, default=1100, help="Row height for bands mode.")

    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = RenderConfig(
        page_width_px=args.page_width_px,
        page_margin_px=args.page_margin_px,
        body_font_size=args.body_font_size,
        code_font_size=args.code_font_size,
        line_height=args.line_height,
        pygments_style=args.pygments_style,
        extra_css_path=args.extra_css_path,
        show_header=args.show_header,
        tight=not args.loose,
        dpi=args.dpi,
        webp_quality=args.webp_quality,
        webp_lossless=args.webp_lossless,
        emit=args.emit,
        manifest=args.manifest,
        hash_tiles=not args.no_hash_tiles,
        tile_mode=args.tile_mode,
        tile_size=args.tile_size,
        tile_overlap=args.tile_overlap,
        band_height=args.band_height,
        linenos=args.linenos,
        input_dir=args.input_dir,
        asset_root=args.asset_root,
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
