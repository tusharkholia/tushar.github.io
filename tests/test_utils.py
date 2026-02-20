from backend.utils import classify_question, extract_tags, sanitize_pdf_text


def test_classify_quant():
    assert classify_question("If x + 2 = 9, what is x?") == "quant_problem_solving"


def test_extract_tags():
    tags = extract_tags("What is the probability of choosing a prime integer?")
    assert "probability" in tags


def test_sanitize_pdf_text():
    assert sanitize_pdf_text("hello\x00 world") == "hello world"
