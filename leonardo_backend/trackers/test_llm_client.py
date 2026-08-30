"""Self-checks for the JSON extraction in llm_client.

No framework and no network: run it with `python3 test_llm_client.py`.
The samples below are real llama-3.1-8b-instant replies captured with a
live key, so this pins the behaviour the parser actually has to survive.
"""

from llm_client import extract_json_object

# Risposta reale. Nota la prosa prima del JSON: il modello ignora
# sistematicamente l'istruzione "OUTPUT FORMAT (JSON ONLY)", quindi questo è
# il caso NORMALE, non un caso limite.
REAL_REPLY = """Mio caro studente, it seems you are struggling to focus. Let us rewrite the summary and begin anew.

{
  "focus_score": 20,
  "summary_so_far": "You started the session, but unfortunately, you've been distracted.",
  "leonardo_comment": "Clear your mind, my friend."
}"""


def test_extracts_json_after_prose():
    out = extract_json_object(REAL_REPLY)
    assert out is not None
    assert out["focus_score"] == 20
    assert out["leonardo_comment"] == "Clear your mind, my friend."


def test_extracts_from_code_fence():
    # Non osservato con questo modello, ma comunissimo altrove: se cambiate
    # modello o provider questo è il primo formato che incontrerete.
    fenced = 'Here you go:\n```json\n{"focus_score": 70}\n```\nHope that helps!'
    assert extract_json_object(fenced) == {"focus_score": 70}


def test_extracts_bare_json():
    assert extract_json_object('{"focus_score": 100}') == {"focus_score": 100}


def test_returns_none_when_unparseable():
    # Il chiamante distingue il fallimento dal successo solo su None, e in quel
    # caso tiene il contesto precedente. Se qui tornasse qualcosa di diverso da
    # None la sessione proseguirebbe con dati inventati.
    assert extract_json_object("I am but a humble painter, not a JSON emitter.") is None
    assert extract_json_object('{"focus_score": }') is None   # JSON malformato
    assert extract_json_object("") is None
    assert extract_json_object(None) is None


def test_rejects_non_objects():
    # rfind('}') su una risposta senza oggetti non deve produrre un tipo strano
    assert extract_json_object("[1, 2, 3]") is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} passed")
