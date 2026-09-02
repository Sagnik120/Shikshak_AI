"""Document parsing package for Shikshak AI RAG module."""

from modules.rag.src.parsing.parser import parse_document, extract_raw_sections
from modules.rag.src.parsing.pdf_parser import parse_pdf
from modules.rag.src.parsing.docx_parser import parse_docx
from modules.rag.src.parsing.pptx_parser import parse_pptx
from modules.rag.src.parsing.txt_parser import parse_text_or_markdown
from modules.rag.src.parsing.structure import detect_language, extract_key_terms_tfidf

__all__ = [
    "parse_document",
    "extract_raw_sections",
    "parse_pdf",
    "parse_docx",
    "parse_pptx",
    "parse_text_or_markdown",
    "detect_language",
    "extract_key_terms_tfidf",
]
