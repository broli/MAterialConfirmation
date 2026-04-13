import pdfplumber

pdf_path = r"raw\Crehan Lisa_ Bath - Estimate Details.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages[1:3]:
        text = page.extract_text()
        print(text)
        print("-" * 50)
