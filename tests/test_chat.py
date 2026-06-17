"""Tests for the Chat CLI interactive loop.

Uses injected callables for answer_callable, input_fn, and output_fn
so no real services are needed.
"""

import pytest
from chat import run_chat


def make_input_fn(*questions, then_raise=EOFError):
    """Return a fake input_fn that yields questions then raises `then_raise`."""
    items = list(questions)

    def _input_fn(prompt=""):
        if items:
            return items.pop(0)
        raise then_raise()

    return _input_fn


def test_loop_reads_question_invokes_callable_prints_answer():
    """The loop reads a question, calls answer_callable, and prints the answer."""
    outputs = []
    answer_callable = lambda q: f"Resposta para: {q}"
    input_fn = make_input_fn("Qual é a capital?", then_raise=EOFError)

    run_chat(answer_callable, input_fn=input_fn, output_fn=outputs.append)

    assert any("Resposta para: Qual é a capital?" in line for line in outputs)


def test_empty_line_exits_cleanly():
    """An empty input line exits the loop without traceback."""
    outputs = []
    answer_callable = lambda q: "should not be called"
    input_fn = make_input_fn("", then_raise=EOFError)

    # Should not raise
    run_chat(answer_callable, input_fn=input_fn, output_fn=outputs.append)


def test_eof_exits_cleanly():
    """EOFError (Ctrl-D) exits the loop cleanly with no traceback."""
    outputs = []
    answer_callable = lambda q: "should not be called"
    # input_fn raises immediately
    input_fn = make_input_fn(then_raise=EOFError)

    # Should not raise
    run_chat(answer_callable, input_fn=input_fn, output_fn=outputs.append)


def test_keyboard_interrupt_exits_cleanly():
    """KeyboardInterrupt (Ctrl-C) exits the loop cleanly with no traceback."""
    outputs = []
    answer_callable = lambda q: "should not be called"
    input_fn = make_input_fn(then_raise=KeyboardInterrupt)

    # Should not raise
    run_chat(answer_callable, input_fn=input_fn, output_fn=outputs.append)


def test_api_error_is_reported_and_loop_continues():
    """A raised exception from answer_callable is reported; the loop continues."""
    outputs = []
    call_count = [0]

    def answer_callable(q):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("API timeout")
        return f"Resposta para: {q}"

    # First question triggers error; second should succeed; then EOF
    input_fn = make_input_fn("Primeira pergunta", "Segunda pergunta", then_raise=EOFError)

    run_chat(answer_callable, input_fn=input_fn, output_fn=outputs.append)

    # Error should be reported
    assert any("API timeout" in line or "Erro" in line or "error" in line.lower() for line in outputs), (
        f"Expected an error message in outputs, got: {outputs}"
    )
    # Second question should produce a valid answer
    assert any("Resposta para: Segunda pergunta" in line for line in outputs), (
        f"Expected answer for second question in outputs, got: {outputs}"
    )
    # Both questions should have been attempted
    assert call_count[0] == 2
