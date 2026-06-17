"""Chat CLI entry point.

.env is loaded here — once, at the entry point — and never inside
imported modules such as config.py or search.py.
"""

from dotenv import load_dotenv
from search import search_prompt


def run_chat(answer_callable, input_fn=input, output_fn=print):
    """Run the interactive question-answer loop.

    Args:
        answer_callable: callable(question: str) -> str that produces the answer.
        input_fn: callable(prompt: str) -> str used to read user input (injectable).
        output_fn: callable(text: str) used to display output (injectable).
    """
    while True:
        try:
            q = input_fn("Faça sua pergunta: ")
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            break

        q = q.strip()
        if not q:
            break

        try:
            answer = answer_callable(q)
            output_fn(answer)
        except Exception as e:
            output_fn(f"Erro ao processar a pergunta: {e}")
            continue


def main():
    chain = search_prompt()

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return

    run_chat(chain.invoke)


if __name__ == "__main__":
    load_dotenv()
    main()
