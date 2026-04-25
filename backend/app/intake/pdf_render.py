from __future__ import annotations


def render_pdf_to_png_pages(pdf_bytes: bytes, *, max_pages: int = 30, zoom: float = 2.0) -> list[tuple[int, bytes]]:
    """
    Rasterize PDF pages to PNG bytes for review UI.

    Returns list of (page_index, png_bytes).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("PyMuPDF (fitz) is required for PDF rendering.") from e

    out: list[tuple[int, bytes]] = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        n = min(doc.page_count, max_pages)
        mat = fitz.Matrix(zoom, zoom)
        for i in range(n):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out.append((i, pix.tobytes("png")))
    finally:
        doc.close()
    return out


def is_pdf(content_type: str) -> bool:
    return (content_type or "").strip().lower() == "application/pdf"


def single_image_as_page(image_bytes: bytes, content_type: str) -> list[tuple[int, bytes]]:
    """Treat one image upload as a single synthetic page for review."""
    ct = (content_type or "").lower()
    if "png" in ct:
        return [(0, image_bytes)]
    # JPEG and others: return as-is; browsers still display image/jpeg
    return [(0, image_bytes)]
