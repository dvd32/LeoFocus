"""Self-checks for the pure logic in trackers.py.

No framework on purpose: run it with `python3 test_trackers.py`.
Everything here must stay free of network, LLM and OS-permission calls.
"""

from trackers import _calculate_grade, is_system_process


def test_grade_boundaries():
    # Ogni soglia va verificata sul valore esatto e su quello sotto, perché
    # gli off-by-one qui finiscono dritti nel report finale.
    assert _calculate_grade(100) == "A+"
    assert _calculate_grade(90) == "A+"
    assert _calculate_grade(89) == "A"
    assert _calculate_grade(85) == "A"
    assert _calculate_grade(84) == "A-"
    assert _calculate_grade(80) == "A-"
    assert _calculate_grade(79) == "B+"
    assert _calculate_grade(75) == "B+"
    assert _calculate_grade(74) == "B"
    assert _calculate_grade(70) == "B"
    assert _calculate_grade(69) == "B-"
    assert _calculate_grade(65) == "B-"
    assert _calculate_grade(64) == "C+"
    assert _calculate_grade(60) == "C+"
    assert _calculate_grade(59) == "C"
    assert _calculate_grade(50) == "C"
    assert _calculate_grade(49) == "D"
    assert _calculate_grade(0) == "D"


def test_system_processes_are_ignored():
    # macOS
    assert is_system_process("Dock")
    assert is_system_process("WindowServer")
    # Windows, incluse le varianti localizzate presenti nella lista
    assert is_system_process("Program Manager")
    assert is_system_process("Seguridad de Windows")
    # Il match è su sottostringa, non su uguaglianza
    assert is_system_process("Task View - 2")


def test_real_windows_are_kept():
    assert not is_system_process("Visual Studio Code")
    assert not is_system_process("Google Chrome")
    assert not is_system_process("leonardoapp")


def test_unusable_window_names_are_ignored():
    assert is_system_process(None)
    assert is_system_process("")
    assert is_system_process(" ")          # troppo corto dopo lo strip
    assert is_system_process("Zoom is sharing your screen")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} passed")
