import base64
import os
from markitdown import MarkItDown
from agent_framework import tool



def get_pdf_as_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    return base64.b64encode(pdf_bytes).decode("utf-8")

@tool(name="fetch_from_wikipedia", description="Fetch HTML content from a URL and convert it to Markdown format.")
def fetch_from_wikipedia() -> str:
    md = MarkItDown()
    html_path = os.path.join(os.path.dirname(__file__), "..", "assets", "AGI_Wikipedia.html")
    result = md.convert(html_path)
    return result