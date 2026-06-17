"""Chat CLI entry point.

.env is loaded here — once, at the entry point — and never inside
imported modules such as config.py or search.py.
"""

from dotenv import load_dotenv
from search import search_prompt


def main():
    chain = search_prompt()

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return

    pass


if __name__ == "__main__":
    load_dotenv()
    main()
