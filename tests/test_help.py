"""Tests for the in-app documentation viewer."""

from __future__ import annotations

import pytest

tk = pytest.importorskip("tkinter")

from lz.help import (  # noqa: E402
    DOCUMENTS,
    DocumentError,
    available_documents,
    display_width,
    docs_root,
    load_document,
    pad,
    render_markdown,
)


# --- locating documents ----------------------------------------------------

def test_every_listed_document_exists_in_the_checkout():
    missing = [p for _, p in DOCUMENTS if not (docs_root() / p).exists()]
    assert not missing, missing


def test_available_documents_matches_the_full_list():
    assert len(available_documents()) == len(DOCUMENTS)


def test_documents_load_and_are_not_empty():
    for _, path in DOCUMENTS:
        assert len(load_document(path)) > 200, path


def test_missing_document_raises_a_clear_error():
    with pytest.raises(DocumentError, match="찾을 수 없습니다"):
        load_document("docs/NOPE.md")


# --- width handling, which is what makes Korean tables line up -------------

def test_hangul_counts_as_two_columns():
    assert display_width("abc") == 3
    assert display_width("한글") == 4
    assert display_width("a한") == 3


def test_padding_uses_display_width_not_character_count():
    # Two cells that pad to the same column must end at the same column.
    assert display_width(pad("한글", 10)) == 10
    assert display_width(pad("abcd", 10)) == 10


def test_padding_never_truncates():
    assert pad("abcdef", 3) == "abcdef"


# --- rendering -------------------------------------------------------------

@pytest.fixture(scope="module")
def root():
    try:
        r = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def text(root):
    widget = tk.Text(root)
    yield widget
    widget.destroy()


def _rendered(widget) -> str:
    return widget.get("1.0", "end")


def test_headings_lose_their_hashes(text):
    render_markdown(text, "# 제목\n\n본문\n")
    out = _rendered(text)
    assert "제목" in out
    assert "#" not in out


def test_heading_gets_a_heading_tag(text):
    render_markdown(text, "## 소제목\n")
    assert "h2" in text.tag_names("1.0")


def test_bold_and_code_markers_are_stripped(text):
    render_markdown(text, "이것은 **굵게** 와 `코드` 입니다\n")
    out = _rendered(text)
    assert "**" not in out
    assert "`" not in out
    assert "굵게" in out and "코드" in out


def test_fenced_code_block_keeps_its_content_verbatim(text):
    render_markdown(text, "```\nscore = a + b\n```\n")
    assert "score = a + b" in _rendered(text)
    assert "```" not in _rendered(text)


def test_table_columns_are_aligned(text):
    render_markdown(
        text,
        "| 위치 | 값 |\n|---|---|\n| a | +0.810 |\n| 아주긴이름 | -0.9 |\n",
    )
    lines = [l for l in _rendered(text).splitlines() if "+0.810" in l or "-0.9" in l]
    assert len(lines) == 2
    # Both value columns must start at the same display column.
    starts = [display_width(l[: l.index("+0.810" if "+0.810" in l else "-0.9")])
              for l in lines]
    assert starts[0] == starts[1], lines


def test_table_separator_row_is_not_printed(text):
    render_markdown(text, "| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert "|---|" not in _rendered(text)


def test_links_are_registered_and_show_only_their_text(text):
    links = render_markdown(text, "자세히는 [점수 문서](docs/SCORING.md) 참고\n")
    out = _rendered(text)
    assert "점수 문서" in out
    assert "docs/SCORING.md" not in out
    assert list(links.values()) == ["docs/SCORING.md"]


def test_blockquote_marker_is_stripped_but_tagged(text):
    render_markdown(text, "> 경고입니다\n")
    out = _rendered(text)
    assert "경고입니다" in out
    assert ">" not in out
    assert "quote" in text.tag_names("1.0")


def test_table_inside_a_blockquote_still_renders_as_a_table(text):
    """DECISIONS.md and SCORING.md both put measurement tables in quotes."""
    render_markdown(text, "> | 마진 | 공동 |\n> |---|---|\n> | 1.0 | -1.20 |\n")
    out = _rendered(text)
    assert "|" not in out
    assert "-1.20" in out


def test_list_items_get_a_bullet(text):
    render_markdown(text, "- 첫째\n- 둘째\n")
    assert "\u2022 첫째" in _rendered(text)


def test_widget_is_left_read_only(text):
    render_markdown(text, "본문\n")
    assert str(text["state"]) == "disabled"


def test_rendering_twice_replaces_rather_than_appends(text):
    render_markdown(text, "첫 번째 문서\n")
    render_markdown(text, "두 번째 문서\n")
    out = _rendered(text)
    assert "첫 번째" not in out
    assert "두 번째" in out


# --- the real documents ----------------------------------------------------

@pytest.mark.parametrize("path", [p for _, p in DOCUMENTS])
def test_every_shipped_document_renders(text, path):
    links = render_markdown(text, load_document(path))
    out = _rendered(text)
    assert len(out) > 200
    assert isinstance(links, dict)


@pytest.mark.parametrize("path", [p for _, p in DOCUMENTS])
def test_no_raw_markup_survives_rendering(text, path):
    """Any marker left on screen means the parser missed a case.\n\n    The first version of this file only checked for fences and table\n    separators, and three real defects slipped past it: markup inside table\n    cells, emphasis wrapping a link, and emphasis spanning a line break.\n    Checking every marker is what catches those.\n    """
    render_markdown(text, load_document(path))
    out = _rendered(text)
    for marker in ("```", "|---", "**", "](", "`"):
        assert marker not in out, (path, marker)


def test_cross_document_links_resolve_to_shipped_documents(text):
    """Links between the docs must land somewhere the viewer can open."""
    names = {p.rsplit("/", 1)[-1] for _, p in DOCUMENTS}
    for _, path in DOCUMENTS:
        links = render_markdown(text, load_document(path))
        for href in links.values():
            if href.startswith(("http://", "https://")) or href.startswith("#"):
                continue
            target = href.split("#", 1)[0].rsplit("/", 1)[-1]
            if target.endswith(".md"):
                assert target in names, (path, href)


# --- regressions for defects the document check caught ---------------------

def test_markup_inside_table_cells_is_stripped(text):
    render_markdown(text, "| `E_core` | **0.5** |\n|---|---|\n| *a*/*d* | 값 |\n")
    out = _rendered(text)
    assert "E_core" in out and "0.5" in out and "a/d" in out
    for marker in ("`", "**", "*"):
        assert marker not in out


def test_bold_wrapping_a_link_renders_the_link(text):
    links = render_markdown(text, "자세히는 **[문서](docs/GUI.md)** 참고\n")
    out = _rendered(text)
    assert "문서" in out
    assert "**" not in out and "](" not in out
    assert list(links.values()) == ["docs/GUI.md"]


def test_emphasis_spanning_a_line_break_is_joined(text):
    render_markdown(text, "이유는 **어디에 어떤 자세로\n붙는지 모르기 때문**입니다\n")
    out = _rendered(text)
    assert "**" not in out
    assert "어디에 어떤 자세로 붙는지 모르기 때문" in out


def test_paragraph_lines_reflow_into_one_line(text):
    """Source line breaks must not become hard breaks in the viewer."""
    render_markdown(text, "첫 줄입니다\n둘째 줄입니다\n\n다음 문단\n")
    lines = [l for l in _rendered(text).splitlines() if l.strip()]
    assert lines[0] == "첫 줄입니다 둘째 줄입니다"
    assert lines[1] == "다음 문단"


def test_wrapped_list_item_stays_in_the_same_bullet(text):
    render_markdown(text, "- **역평행** — 평행만 가정합니다.\n  경고가 뜹니다.\n")
    lines = [l for l in _rendered(text).splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("• ")
    assert "경고가 뜹니다" in lines[0]


def test_headings_do_not_absorb_the_following_paragraph(text):
    render_markdown(text, "## 제목\n본문입니다\n")
    lines = [l for l in _rendered(text).splitlines() if l.strip()]
    assert lines == ["제목", "본문입니다"]
