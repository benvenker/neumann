"""Canonical document ID generation for Neumann pipeline.

Provides a single source of truth for doc_id computation across render,
summarize, and index modules. Ensures consistency and handles spaces
by replacing them with underscores.
"""

from pathlib import Path


def make_doc_id(path: Path, input_root: Path | None = None) -> str:
    """Generate canonical doc_id from file path.

    Computes a stable, URL-friendly identifier by:
    - Computing relative path from input_root (if provided)
    - Removing path anchor for absolute paths when input_root not provided
    - Replacing spaces with underscores in each path part
    - Joining parts with double underscores

    Args:
        path: File path (absolute or relative)
        input_root: Optional root directory for relative path computation

    Returns:
        doc_id string with spaces replaced by underscores

    Examples:
        >>> make_doc_id(Path("a/b c.md"), Path("a"))
        'b_c.md'
        >>> make_doc_id(Path("docs/hello world.py"))
        'docs__hello_world.py'
    """
    parts: list[str]
    if input_root is not None:
        rel = path.relative_to(input_root)
        parts = list(rel.parts)
    else:
        parts = list(path.parts)
        anchor = path.anchor
        if anchor:
            parts = [p for p in parts if p and p != anchor]
    return "__".join(p.replace(" ", "_") for p in parts)


def make_doc_id_from_str(source_path: str) -> str:
    """Generate doc_id from string path (convenience wrapper).

    Args:
        source_path: File path as string

    Returns:
        doc_id string with spaces replaced by underscores
    """
    return make_doc_id(Path(source_path))


__all__ = ["make_doc_id", "make_doc_id_from_str"]

