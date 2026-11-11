"""In-app documentation viewer.

Someone who only has lz.exe cannot read the project's Markdown files, and
the scoring caveats are not optional reading -- an uncalibrated ranking
mistaken for an affinity is the easiest way to waste a synthesis. So the
documents ship inside the executable and the app renders them itself.

A small Markdown renderer rather than a dependency or a browser hand-off:
the viewer has to work from a frozen one-file build with no network and no
assumption about what opens a .md file on the user's machine.
"""

from __future__ import annotations

import re
import sys
import unicodedata
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk

# Shown in the picker, in reading order. Paths are relative to the project
# root and are preserved inside the bundle.
DOCUMENTS: list[tuple[str, str]] = [
    ("사용법 (README)", "README.md"),
    ("앱 사용 설명서", "docs/GUI.md"),
    ("점수 산정 기준", "docs/SCORING.md"),
    ("설계 기록 (DECISIONS)", "DECISIONS.md"),
    ("기여 안내 (CONTRIBUTING)", "CONTRIBUTING.md"),
]

BODY_FONT = ("Malgun Gothic", 10)
MONO_FONT = ("Consolas", 9)


class DocumentError(LookupError):
    """Raised when a document cannot be found or read."""


def docs_root() -> Path:
    """Where the Markdown lives, frozen or not.

    PyInstaller unpacks a one-file build to sys._MEIPASS; from a checkout
    the documents sit at the project root. Resolving this wrongly is the
    classic packaging failure: the app runs, and only the Help button is
    broken.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is not None:
        return Path(base)
    return Path(__file__).resolve().parent.parent


def available_documents() -> list[tuple[str, str]]:
    """The subset of DOCUMENTS actually present."""
    root = docs_root()
    return [(t, p) for t, p in DOCUMENTS if (root / p).exists()]


def load_document(relative_path: str) -> str:
    path = docs_root() / relative_path
    if not path.exists():
        raise DocumentError(f"문서를 찾을 수 없습니다: {relative_path}")
    # utf-8-sig: these files are edited on Windows and may carry a BOM.
    return path.read_text(encoding="utf-8-sig")


def display_width(text: str) -> int:
    """Column width of `text` in a monospace font.

    Hangul and other East Asian characters occupy two cells. Padding table
    columns by len() instead lines up the English tables and shreds every
    Korean one, which is most of them here.
    """
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text
    )


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


# --- Markdown rendering ----------------------------------------------------

_INLINE = re.compile(
    r"\*\*(?P<bold>[^*]+)\*\*"
    r"|(?<!\*)\*(?P<italic>[^*\n]+)\*(?!\*)"
    r"|`(?P<code>[^`]+)`"
    r"|\[(?P<link>[^\]]+)\]\((?P<href>[^)]+)\)"
)

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_LIST = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
_RULE = re.compile(r"^\s*([-*_])\1{2,}\s*$")


def configure_tags(widget: tk.Text) -> None:
    """Define every tag the renderer uses."""
    widget.configure(font=BODY_FONT, spacing1=1, spacing3=2, wrap="word")
    widget.tag_configure("h1", font=("Malgun Gothic", 16, "bold"),
                         spacing1=14, spacing3=8)
    widget.tag_configure("h2", font=("Malgun Gothic", 13, "bold"),
                         spacing1=12, spacing3=6)
    widget.tag_configure("h3", font=("Malgun Gothic", 11, "bold"),
                         spacing1=10, spacing3=4)
    widget.tag_configure("h4", font=("Malgun Gothic", 10, "bold"),
                         spacing1=8, spacing3=3)
    widget.tag_configure("bold", font=("Malgun Gothic", 10, "bold"))
    widget.tag_configure("italic", font=("Malgun Gothic", 10, "italic"))
    widget.tag_configure("code", font=MONO_FONT, background="#f2f2f2")
    widget.tag_configure("block", font=MONO_FONT, background="#f6f8fa",
                         lmargin1=20, lmargin2=20, spacing1=0, spacing3=0,
                         wrap="none")
    widget.tag_configure("table", font=MONO_FONT, lmargin1=20, lmargin2=20,
                         spacing1=0, spacing3=0, wrap="none")
    widget.tag_configure("quote", background="#fff8e1", lmargin1=16,
                         lmargin2=16, rmargin=8)
    widget.tag_configure("bullet", lmargin1=20, lmargin2=36)
    widget.tag_configure("rule", font=("Malgun Gothic", 1))
    widget.tag_configure("link", foreground="#0b62c4", underline=True)


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        set(c) <= set("-: ") and "-" in c for c in cells
    )


def _render_table(widget: tk.Text, rows: list[list[str]], extra: tuple) -> None:
    """Lay a pipe table out as aligned monospace text."""
    body = [[strip_inline(c) for c in r] for r in rows if not _is_separator(r)]
    if not body:
        return
    columns = max(len(r) for r in body)
    body = [r + [""] * (columns - len(r)) for r in body]
    widths = [
        max(display_width(r[i]) for r in body) for i in range(columns)
    ]

    for index, row in enumerate(body):
        line = "  ".join(pad(cell, widths[i]) for i, cell in enumerate(row))
        tags = ("table",) + extra
        if index == 0:
            tags = tags + ("bold",)
        widget.insert("end", line.rstrip() + "\n", tags)
        if index == 0:
            underline = "  ".join("-" * w for w in widths)
            widget.insert("end", underline + "\n", ("table",) + extra)


def strip_inline(text: str) -> str:
    """Markup removed, leaving the text a reader should see.

    Used for table cells: they are laid out in a monospace grid, so their
    width has to be the width of what is actually displayed. Leaving the
    markers in both widened the column and printed raw `backticks` and
    **asterisks** inside the table.
    """
    previous = None
    while previous != text:
        previous = text
        text = _INLINE.sub(
            lambda m: m.group("bold") or m.group("italic")
            or m.group("code") or m.group("link"),
            text,
        )
    return text


def _render_inline(widget: tk.Text, text: str, extra: tuple, links: dict) -> None:
    """Insert `text`, converting inline markup to tags.

    Recurses into bold and italic spans, because emphasis wrapping a link --
    `**[doc](doc.md)**` -- is common in these documents and a single pass
    would print the link syntax verbatim inside the bold run.
    """
    position = 0
    for match in _INLINE.finditer(text):
        if match.start() > position:
            widget.insert("end", text[position:match.start()], extra)
        if match.group("bold"):
            _render_inline(widget, match.group("bold"), extra + ("bold",), links)
        elif match.group("italic"):
            _render_inline(widget, match.group("italic"), extra + ("italic",), links)
        elif match.group("code"):
            widget.insert("end", match.group("code"), extra + ("code",))
        else:
            name = f"link-{len(links)}"
            links[name] = match.group("href")
            _render_inline(widget, match.group("link"),
                           extra + ("link", name), links)
        position = match.end()
    if position < len(text):
        widget.insert("end", text[position:], extra)


def render_markdown(widget: tk.Text, markdown: str) -> dict[str, str]:
    """Draw `markdown` into `widget`. Returns {tag_name: href} for links."""
    configure_tags(widget)
    widget.configure(state="normal")
    widget.delete("1.0", "end")

    links: dict[str, str] = {}
    in_code_block = False
    table: list[list[str]] = []
    table_tags: tuple = ()
    # Consecutive body lines are joined into one paragraph before inline
    # markup is parsed. Rendering line by line hard-wraps the text at
    # whatever width the source file happened to use, and -- worse -- misses
    # any **emphasis** or [link](x) that spans a line break.
    para: list[str] = []
    para_tags: tuple = ()
    para_prefix = ""

    def flush_table() -> None:
        nonlocal table
        if table:
            _render_table(widget, table, table_tags)
            table = []

    def flush_para() -> None:
        nonlocal para, para_prefix
        if para:
            if para_prefix:
                widget.insert("end", para_prefix, para_tags)
            _render_inline(widget, " ".join(para), para_tags, links)
            widget.insert("end", "\n", para_tags)
            para = []
            para_prefix = ""

    def flush() -> None:
        flush_table()
        flush_para()

    for raw in markdown.splitlines():
        line = raw.rstrip()

        # Blockquote: strip the marker and keep processing, so tables and
        # code inside a quote still render as tables and code.
        extra: tuple = ()
        if line.lstrip().startswith(">"):
            line = line.lstrip()[1:].lstrip(" ")
            extra = ("quote",)

        if line.strip().startswith("```"):
            flush()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            widget.insert("end", line + "\n", ("block",) + extra)
            continue

        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush_para()
            if not table:
                table_tags = extra
            table.append(_split_row(line))
            continue
        flush_table()

        if not line.strip():
            flush_para()
            widget.insert("end", "\n", extra)
            continue

        if _RULE.match(line):
            flush_para()
            widget.insert("end", "─" * 60 + "\n", ("rule",) + extra)
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_para()
            level = min(len(heading.group(1)), 4)
            _render_inline(widget, heading.group(2), extra + (f"h{level}",), links)
            widget.insert("end", "\n", extra + (f"h{level}",))
            continue

        item = _LIST.match(line)
        if item:
            flush_para()
            marker = "• " if item.group(2) in "-*" else f"{item.group(2)} "
            para_prefix = " " * len(item.group(1)) + marker
            para_tags = extra + ("bullet",)
            para = [item.group(3)]
            continue

        # A plain line continues the paragraph or list item above it.
        if para:
            para.append(line.strip())
        else:
            para_tags = extra
            para = [line.strip()]

    flush()
    widget.configure(state="disabled")
    return links


# --- the window ------------------------------------------------------------

class HelpWindow(tk.Toplevel):
    """A document picker beside a rendered Markdown pane."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("lz - 문서")
        self.geometry("980x760")
        self._links: dict[str, str] = {}
        self._documents = available_documents()

        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        picker = ttk.Frame(frame)
        picker.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.listbox = tk.Listbox(picker, width=24, exportselection=False,
                                  font=BODY_FONT, activestyle="none")
        self.listbox.pack(fill="y", expand=True)
        for title, _ in self._documents:
            self.listbox.insert("end", title)
        self.listbox.bind("<<ListboxSelect>>", self._on_pick)

        pane = ttk.Frame(frame)
        pane.grid(row=0, column=1, sticky="nsew")
        pane.columnconfigure(0, weight=1)
        pane.rowconfigure(0, weight=1)

        self.text = tk.Text(pane, padx=14, pady=10, borderwidth=1,
                            relief="solid", cursor="arrow")
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(pane, orient="vertical", command=self.text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scroll.set)

        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status, foreground="#555").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        self.bind("<Escape>", lambda _e: self.destroy())
        self.text.bind("<MouseWheel>", self._on_wheel)

        if self._documents:
            self.listbox.selection_set(0)
            self.show(0)
        else:
            configure_tags(self.text)
            self.text.insert(
                "1.0",
                "문서 파일을 찾을 수 없습니다.\n\n"
                "소스에서 실행 중이라면 저장소 루트에서 실행하세요.\n"
                "exe라면 문서가 번들에 포함되지 않은 빌드입니다.",
            )
            self.text.configure(state="disabled")

    def show(self, index: int) -> None:
        title, path = self._documents[index]
        try:
            markdown = load_document(path)
        except DocumentError as exc:
            configure_tags(self.text)
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.insert("1.0", str(exc))
            self.text.configure(state="disabled")
            self.status.set("읽기 실패")
            return

        self._links = render_markdown(self.text, markdown)
        for name, href in self._links.items():
            self.text.tag_bind(name, "<Button-1>",
                               lambda _e, h=href: self._follow(h))
            self.text.tag_bind(name, "<Enter>",
                               lambda _e: self.text.configure(cursor="hand2"))
            self.text.tag_bind(name, "<Leave>",
                               lambda _e: self.text.configure(cursor="arrow"))
        self.text.yview_moveto(0)
        self.status.set(f"{path}  -  링크를 클릭하면 이동합니다. Esc로 닫기.")

    def _on_pick(self, _event) -> None:
        selection = self.listbox.curselection()
        if selection:
            self.show(selection[0])

    def _on_wheel(self, event) -> str:
        self.text.yview_scroll(-event.delta // 120, "units")
        return "break"

    def _follow(self, href: str) -> None:
        """Follow a link: in-bundle documents switch panes, URLs open a browser."""
        if href.startswith(("http://", "https://")):
            webbrowser.open(href)
            return

        target = href.split("#", 1)[0].lstrip("./")
        target = target.replace("../", "")
        for index, (_title, path) in enumerate(self._documents):
            if path.endswith(target) or target.endswith(Path(path).name):
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(index)
                self.show(index)
                return
        self.status.set(f"이 문서는 앱에 포함되어 있지 않습니다: {href}")


def open_help(master: tk.Misc) -> HelpWindow:
    window = HelpWindow(master)
    window.transient(master.winfo_toplevel())
    window.focus_set()
    return window
