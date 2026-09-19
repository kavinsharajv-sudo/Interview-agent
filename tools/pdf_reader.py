# tools/pdf_reader.py
import pypdf
from langchain_core.tools import tool

@tool
def extract_pdf_text(file_path: str) -> str:
    """Extract plain text from a PDF resume file."""
    reader = pypdf.PdfReader(file_path)
    pages  = [page.extract_text() or "" for page in reader.pages]
    text   = "\n".join(pages).strip()

    if not text:
        return f"ERROR: could not extract text from {file_path}"

    return text
