import fitz
from docx import Document
import mimetypes

def extract_from_pdf(file_path, min_len=40):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return [p.strip() for p in text.split("\n") if len(p.strip()) > min_len]

def extract_from_docx(file_path, min_len=40):
    doc = Document(file_path)
    return [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > min_len]

def extract_from_txt(file_path, min_len=40):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if len(line.strip()) > min_len]

def extract_chunks(file_path, min_len=40):
    mime = mimetypes.guess_type(file_path)[0]
    if mime == "application/pdf":
        return extract_from_pdf(file_path, min_len)
    elif mime in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return extract_from_docx(file_path, min_len)
    elif mime == "text/plain":
        return extract_from_txt(file_path, min_len)
    else:
        raise ValueError(f"Unsupported file type: {mime}")
