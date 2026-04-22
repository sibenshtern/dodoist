"""
Server-side ProseMirror JSON sanitizer.

Enforces a strict allowlist of node types and marks, stripping anything
not on the list. This prevents stored XSS via crafted description/comment JSON
that a renderer might execute.
"""

from urllib.parse import urlparse

ALLOWED_NODES = {
    "doc", "paragraph", "heading", "blockquote",
    "bulletList", "orderedList", "listItem",
    "codeBlock", "hardBreak", "text",
    # mention nodes (used for @-mentions in comments)
    "mention",
}

ALLOWED_MARKS = {"bold", "italic", "strike", "code", "link"}

# Schemes allowed in link hrefs
ALLOWED_SCHEMES = {"http", "https", "mailto"}


def _safe_href(href: str) -> str | None:
    """Return href if the scheme is safe, else None."""
    if not href:
        return None
    try:
        scheme = urlparse(href).scheme.lower()
    except Exception:
        return None
    return href if scheme in ALLOWED_SCHEMES else None


def _sanitize_mark(mark: dict) -> dict | None:
    """Return a sanitized mark dict, or None to drop it."""
    mark_type = mark.get("type")
    if mark_type not in ALLOWED_MARKS:
        return None
    if mark_type == "link":
        href = _safe_href((mark.get("attrs") or {}).get("href", ""))
        if not href:
            return None
        return {"type": "link", "attrs": {"href": href}}
    return {"type": mark_type}


def _sanitize_node(node: dict) -> dict | None:
    """
    Recursively sanitize a ProseMirror node.
    Returns the sanitized node, or None to drop it entirely.
    """
    if not isinstance(node, dict):
        return None

    node_type = node.get("type")
    if node_type not in ALLOWED_NODES:
        return None

    result: dict = {"type": node_type}

    # Preserve text content
    if "text" in node:
        result["text"] = str(node["text"])

    # Sanitize attrs (allowlisted per node type)
    attrs = node.get("attrs") or {}
    if node_type == "heading":
        level = attrs.get("level", 1)
        result["attrs"] = {"level": int(level) if isinstance(level, int) else 1}
    elif node_type == "mention":
        result["attrs"] = {"id": str(attrs.get("id", "")), "label": str(attrs.get("label", ""))}
    elif node_type == "codeBlock":
        result["attrs"] = {"language": str(attrs.get("language", ""))}

    # Sanitize marks
    raw_marks = node.get("marks", [])
    if isinstance(raw_marks, list):
        safe_marks = [m for m in (_sanitize_mark(m) for m in raw_marks) if m is not None]
        if safe_marks:
            result["marks"] = safe_marks

    # Recurse into children
    raw_content = node.get("content", [])
    if isinstance(raw_content, list):
        safe_content = [c for c in (_sanitize_node(c) for c in raw_content) if c is not None]
        if safe_content:
            result["content"] = safe_content

    return result


def sanitize(doc: dict | None) -> dict | None:
    """
    Entry point. Accepts the full ProseMirror doc JSON and returns a sanitized copy.
    Returns None if the input is falsy.
    """
    if not doc:
        return doc
    if not isinstance(doc, dict):
        return None
    if doc.get("type") != "doc":
        return None
    return _sanitize_node(doc)
