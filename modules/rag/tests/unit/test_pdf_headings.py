"""PDF headings are found anywhere on a page, and running headers are dropped.

Only the first line of each page used to be checked. Real PDFs start every
page with a running header, so almost no headings were detected, chunks had
no section titles, and the header/footer text was embedded in every chunk.
"""
import io
import textwrap

from modules.rag.src.parsing.pdf_parser import _repeated_lines, parse_pdf


def _pdf(pages: list[list[str]]) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["pdf.fonttype"] = 42
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        for n, lines in enumerate(pages, start=1):
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.08, 0.96, "Motion Notes — Class 9 Science", fontsize=8)
            y = 0.9
            for line in lines:
                for part in textwrap.wrap(line, 90) or [""]:
                    fig.text(0.08, y, part, fontsize=10)
                    y -= 0.025
            fig.text(0.5, 0.03, f"Page {n}", fontsize=8)
            pdf.savefig(fig)
            plt.close(fig)
    return buf.getvalue()


BODY = "Force changes the motion of an object and is measured in newtons in every experiment we do."


def test_headings_mid_page_are_detected_and_sections_split():
    data = _pdf([
        ["1.1 Balanced Forces", BODY, "1.2 Unbalanced Forces", BODY],
        [BODY, "1.3 Inertia", BODY],
        ["1.4 Momentum", BODY],
    ])
    sections, chapters = parse_pdf(data)
    assert chapters == ["1.1 Balanced Forces", "1.2 Unbalanced Forces", "1.3 Inertia", "1.4 Momentum"]
    titled = [(s.section_title, s.page_or_slide) for s in sections]
    assert ("1.2 Unbalanced Forces", 1) in titled and ("1.3 Inertia", 2) in titled
    # Text at the top of page 2 continues the section from page 1.
    assert titled[titled.index(("1.3 Inertia", 2)) - 1] == ("1.2 Unbalanced Forces", 2)


def test_running_headers_and_page_numbers_are_removed():
    data = _pdf([["1.1 A", BODY], ["1.2 B", BODY], ["1.3 C", BODY]])
    sections, _ = parse_pdf(data)
    text = "\n".join(s.raw_text for s in sections)
    assert "Class 9 Science" not in text and "Page 2" not in text
    assert BODY.split()[0] in text


def test_repeated_line_detection_needs_most_pages():
    pages = ["Header\nPage 1\nalpha", "Header\nPage 2\nbeta", "Other\nPage 3\ngamma", "Header\nPage 4\ndelta"]
    repeated = _repeated_lines(pages)
    assert "header" in repeated and "page #" in repeated and "alpha" not in repeated
    assert _repeated_lines(["Header\nx", "Header\ny"]) == set()  # too few pages to tell
