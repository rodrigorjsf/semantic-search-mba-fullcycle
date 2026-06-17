"""Shared configuration helper.

Usage at entry points (chat.py, ingest.py):
    from dotenv import load_dotenv
    load_dotenv()                # load .env once, at the entry point

Then anywhere in the app:
    from config import req
    api_key = req("GOOGLE_API_KEY")

IMPORTANT: load_dotenv() must NEVER be called in this module or any
other imported module — only at the program entry points.

Required settings:
    GOOGLE_API_KEY
    DATABASE_URL
    PG_VECTOR_COLLECTION_NAME
    GOOGLE_EMBEDDING_MODEL
    PDF_PATH
"""

import os


def req(name: str) -> str:
    """Return the value of environment variable *name*.

    Raises:
        SystemExit: with a descriptive message naming *name* when the
            variable is absent or empty.
    """
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Required environment variable '{name}' is missing or empty. "
            f"Set it in your .env file or shell environment."
        )
    return value
