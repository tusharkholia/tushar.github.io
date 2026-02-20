from backend.explain_engine import ExplainEngine


def test_explain_fallback_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    engine = ExplainEngine()
    result = engine.explain("If 2x=10, what is x?")
    assert "ANSWER" in result
    assert "STEP-BY-STEP SOLUTION" in result
