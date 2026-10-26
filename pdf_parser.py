import pdfplumber

def extract_text(uploaded_file):
    pages = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n".join(pages)