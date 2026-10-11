from src.core.subjects import readable_subject_label


def test_bare_grade_code_resolves_to_display_name():
    assert readable_subject_label("G12-ENG") == "English Core"


def test_display_name_passes_through():
    assert readable_subject_label("English Core") == "English Core"


def test_unmapped_grade_code_passes_through():
    assert readable_subject_label("G99-XYZ") == "G99-XYZ"


def test_stream_code_passes_through_when_unmapped():
    assert readable_subject_label("default-2026-g11-commerce") == "default-2026-g11-commerce"


def test_none_passes_through():
    assert readable_subject_label(None) is None
