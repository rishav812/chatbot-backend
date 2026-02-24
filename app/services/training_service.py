import io

from pypdf import PdfReader


async def bot_training(file_bytes: bytes, file_name: str) -> str:
    """
    Extract all text from a PDF file into a single string.

    Args:
        file_bytes: Raw PDF content.
        file_name: Original filename (for logging / future use).

    Returns:
        The full extracted text of the PDF.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text)
    print(f"✅ bot_training completed for '{file_name}' — {len(pages_text)} page(s), {len(full_text)} chars")
    return full_text
