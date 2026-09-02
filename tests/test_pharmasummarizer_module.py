from modules.pharmasummarizer_module import (
    extract_key_highlights,
    find_body_sentences,
    summarize_text,
)


REGULATORY_DOCUMENT_TEXT = """
This guideline describes pharmacovigilance requirements for monitoring medicinal
products and reporting safety information to appropriate regulatory authorities.

Revision 2 contains the following changes to this pharmacovigilance guideline
and its implementation schedule for regulated organizations.

Adopted by CHMP following review of the revised implementation timeline and
supporting regulatory documentation.

Sponsors should maintain appropriate safety monitoring and reporting procedures
throughout the medicinal product lifecycle.
"""


FALLBACK_DOCUMENT_TEXT = """
Regulated organizations maintain safety monitoring controls for medicinal
products throughout routine operational activities.

Revision 2 contains the following changes to the implementation schedule for
regulated organizations and associated documentation.

Adopted by CHMP following review of the revised implementation timeline and
supporting regulatory documentation.

Sponsors maintain documented reporting controls for medicinal product safety
throughout routine operational activities.
"""


LEGITIMATE_REVISION_TEXT = """
This guideline describes document control expectations for regulated quality
systems and associated operating procedures.

Revision control is required to ensure approved procedures remain current,
traceable, and appropriately documented.
"""


def test_revision_history_sentences_are_excluded_from_body_candidates():
    sentences = find_body_sentences(REGULATORY_DOCUMENT_TEXT)
    combined = " ".join(sentences).lower()

    assert "pharmacovigilance requirements" in combined
    assert "safety monitoring and reporting procedures" in combined

    assert "revision 2 contains" not in combined
    assert "adopted by chmp" not in combined


def test_revision_history_sentences_are_excluded_from_summary():
    summary = summarize_text(REGULATORY_DOCUMENT_TEXT).lower()

    assert "pharmacovigilance requirements" in summary
    assert "revision 2 contains" not in summary
    assert "adopted by chmp" not in summary


def test_revision_history_sentences_are_excluded_from_highlights():
    highlights = extract_key_highlights(REGULATORY_DOCUMENT_TEXT)
    combined = " ".join(highlights).lower()

    assert "revision 2 contains" not in combined
    assert "adopted by chmp" not in combined


def test_revision_history_filter_is_applied_in_fallback_body_selection():
    sentences = find_body_sentences(FALLBACK_DOCUMENT_TEXT)
    combined = " ".join(sentences).lower()

    assert "safety monitoring controls" in combined
    assert "documented reporting controls" in combined

    assert "revision 2 contains" not in combined
    assert "adopted by chmp" not in combined


def test_legitimate_revision_control_content_is_not_filtered():
    sentences = find_body_sentences(LEGITIMATE_REVISION_TEXT)
    combined = " ".join(sentences).lower()

    assert "revision control is required" in combined
