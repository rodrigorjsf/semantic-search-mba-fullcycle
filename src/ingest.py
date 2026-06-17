"""PDF ingestion entry point.

.env is loaded here — once, at the entry point — and never inside
imported modules such as config.py or search.py.
"""

from dotenv import load_dotenv
from config import req


def ingest_pdf():
    pdf_path = req("PDF_PATH")
    pass


if __name__ == "__main__":
    load_dotenv()
    ingest_pdf()
