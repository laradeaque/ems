import re
from docx import Document

PLACEHOLDER_PATTERN = re.compile(r"\[([A-Za-z0-9_]+)\]")

def get_placeholders(docx_path=""):
    """
    Extract all placeholders like [NAME], [MAT_1], [TEST_0]
    from a .docx file.

    Returns:
        list[str]: Unique placeholders (without brackets),
                   in the order they first appear.
    """
    if not docx_path:
        return []
    doc = Document(docx_path)
    placeholders = []

    def extract(text):
        for match in PLACEHOLDER_PATTERN.findall(text):
            if match not in placeholders:
                placeholders.append(match)

    # Normal paragraphs
    for paragraph in doc.paragraphs:
        extract(paragraph.text)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                extract(cell.text)

    return placeholders