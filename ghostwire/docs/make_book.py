"""GHOSTWIRE cryptography book generator.

Assembles the full PDF from book_part_*.py modules.  Run:

    python3 make_book.py            -> GHOSTWIRE_Cryptography_Book.pdf
"""
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)          # so parts can import gw.*
sys.path.insert(0, HERE)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, Preformatted, PageBreak,
                                Table, TableStyle, NextPageTemplate)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.tableofcontents import TableOfContents

PAGE_W, PAGE_H = A4


class BookDoc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, **kw)
        margin = 20 * mm
        frame = Frame(margin, margin, PAGE_W - 2 * margin,
                      PAGE_H - 2 * margin, id="main")
        self.addPageTemplates([PageTemplate(id="all", frames=[frame],
                                            onPage=self._chrome)])
        self.page_count_hack = [0]

    def _chrome(self, canvas, doc):
        self.page_count_hack[0] += 1
        canvas.saveState()
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(colors.HexColor("#5a6b5c"))
        canvas.drawString(20 * mm, 12 * mm,
                          "GHOSTWIRE // APPLIED CRYPTOGRAPHY & PROTOCOL "
                          "ENGINEERING")
        canvas.drawRightString(PAGE_W - 20 * mm, 12 * mm,
                               "page %d" % doc.page)
        canvas.setStrokeColor(colors.HexColor("#243527"))
        canvas.line(20 * mm, 15 * mm, PAGE_W - 20 * mm, 15 * mm)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name == "h1":
                self.notify("TOCEntry", (0, flowable.getPlainText(),
                                         self.page))
            elif name == "h2":
                self.notify("TOCEntry", (1, flowable.getPlainText(),
                                         self.page))


ST = {}


def _styles():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import glob
    dirs = ["/usr/share/fonts/truetype/dejavu/",
            "/usr/local/lib/python3.13/site-packages/cv2/qt/fonts/"]
    # Expand to any dejavu dir on the box (survives sandbox resets).
    dirs += [os.path.dirname(p) + "/" for p in
             glob.glob("/usr/**/DejaVuSans.ttf", recursive=True)]

    def find(fn):
        for d in dirs:
            if os.path.exists(d + fn):
                return d + fn
        raise FileNotFoundError(fn)

    for name, fn in [("DejaVu", "DejaVuSans.ttf"),
                     ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
                     ("DejaVu-Oblique", "DejaVuSans-Oblique.ttf"),
                     ("DejaVuMono", "DejaVuSansMono.ttf"),
                     ("DejaVuMono-Bold", "DejaVuSansMono-Bold.ttf")]:
        try:
            pdfmetrics.getFont(name)
        except KeyError:
            try:
                pdfmetrics.registerFont(TTFont(name, find(fn)))
            except FileNotFoundError:
                # Fall back to a close sibling if one face is missing.
                sub = {"DejaVu-Oblique": "DejaVuSans.ttf"}.get(fn)
                if sub:
                    pdfmetrics.registerFont(TTFont(name, find(sub)))
                else:
                    raise
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVu-Bold",
        italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")
    S = ParagraphStyle
    ST["body"] = S("body", fontName="DejaVu", fontSize=10, leading=14.5,
                   alignment=TA_JUSTIFY, spaceAfter=6)
    ST["bodyc"] = S("bodyc", parent=ST["body"], alignment=TA_CENTER)
    ST["h1"] = S("h1", fontName="DejaVu-Bold", fontSize=21, leading=26,
                 textColor=colors.HexColor("#0d3a22"), spaceBefore=8,
                 spaceAfter=14)
    ST["h2"] = S("h2", fontName="DejaVu-Bold", fontSize=13.5, leading=18,
                 textColor=colors.HexColor("#14522f"), spaceBefore=12,
                 spaceAfter=6)
    ST["h3"] = S("h3", fontName="DejaVu-Bold", fontSize=11, leading=15,
                 textColor=colors.HexColor("#1d6a3f"), spaceBefore=8,
                 spaceAfter=4)
    ST["h2nc"] = S("h2nc", parent=ST["h2"])  # h2 not indexed in the TOC
    ST["code"] = S("code", fontName="DejaVuMono", fontSize=7.2, leading=9.2,
                   textColor=colors.HexColor("#122015"),
                   backColor=colors.HexColor("#eef3ee"), borderPadding=4)
    ST["vec"] = S("vec", fontName="DejaVuMono", fontSize=6.6, leading=8.4,
                  textColor=colors.HexColor("#20301f"))
    ST["note"] = S("note", fontName="DejaVu-Oblique", fontSize=9,
                   leading=12.5, textColor=colors.HexColor("#3c4a3d"),
                   leftIndent=10, spaceAfter=6)
    ST["bullet"] = S("bullet", parent=ST["body"], leftIndent=14,
                     bulletIndent=4, spaceAfter=3)
    ST["cover"] = S("cover", fontName="DejaVu-Bold", fontSize=34,
                    leading=40, textColor=colors.HexColor("#0d3a22"),
                    alignment=TA_CENTER)
    ST["coversub"] = S("coversub", fontName="DejaVu", fontSize=13,
                       leading=18, textColor=colors.HexColor("#33473a"),
                       alignment=TA_CENTER)
    return ST


class Flow:
    """Collector of platypus flowables + tiny authoring API."""

    def __init__(self):
        self.items = []
        self.st = _styles()

    # -- structural ---------------------------------------------------
    def part(self, title):
        self.items.append(PageBreak())
        self.items.append(Spacer(1, 60 * mm))
        self.items.append(Paragraph(title, self.st["cover"]))

    def chapter(self, title):
        self.items.append(PageBreak())
        self.items.append(Paragraph(title, self.st["h1"]))

    def h2(self, t):
        self.items.append(Paragraph(t, self.st["h2"]))

    def h3(self, t):
        self.items.append(Paragraph(t, self.st["h3"]))

    def p(self, t):
        self.items.append(Paragraph(t, self.st["body"]))

    def pc(self, t):
        self.items.append(Paragraph(t, self.st["bodyc"]))

    def note(self, t):
        self.items.append(Paragraph("NOTE — " + t, self.st["note"]))

    def bullets(self, rows):
        for r in rows:
            self.items.append(Paragraph("•  " + r, self.st["bullet"]))

    def code(self, text, caption=None, width=88):
        if caption:
            self.h3(caption)
        out = []
        for line in textwrap.dedent(text).strip("\n").split("\n"):
            if len(line) <= width:
                out.append(line)
            else:
                while len(line) > width:
                    cut = line.rfind(" ", 40, width)
                    if cut < 0:
                        cut = width
                    out.append(line[:cut])
                    line = "      " + line[cut:].lstrip()
                out.append(line)
        self.items.append(Preformatted("\n".join(out), self.st["code"]))

    def vec(self, text, width=88):
        out = []
        for line in text.split("\n"):
            while len(line) > width:
                out.append(line[:width])
                line = "        " + line[width:]
            out.append(line)
        self.items.append(Preformatted("\n".join(out), self.st["vec"]))

    def table(self, rows, widths=None, header=True):
        if widths is None:
            widths = [481.9 / len(rows[0])] * len(rows[0])
        hst = ParagraphStyle("th", fontName="DejaVu-Bold", fontSize=8.5,
                             leading=11)
        cst = ParagraphStyle("td", fontName="DejaVuMono", fontSize=7.4,
                             leading=9.6)
        data = [[Paragraph(str(c), hst if (header and ri == 0) else cst)
                 for c in row] for ri, row in enumerate(rows)]
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcebde")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9db8a0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f2f7f2")]),
        ]))
        self.items.append(t)
        self.items.append(Spacer(1, 6))

    def sp(self, h=6):
        self.items.append(Spacer(1, h))


def build():
    flow = Flow()

    import book_front, book_part1, book_part2, book_part3
    import book_part4, book_part5, book_part6, book_part7
    import book_part8, book_appendix
    for mod in (book_front, book_part1, book_part2, book_part3,
                book_part4, book_part5, book_part6, book_part7,
                book_part8, book_appendix):
        mod.build(flow)

    out = os.path.join(HERE, "GHOSTWIRE_Cryptography_Book.pdf")
    doc = BookDoc(out, title="GHOSTWIRE Applied Cryptography",
                  author="GHOSTWIRE Project (@Ariko & Arena)")
    doc.multiBuild(flow.items)
    from pypdf import PdfReader
    pages = len(PdfReader(out).pages)
    print("BOOK BUILT:", out, "pages:", pages)
    return pages


if __name__ == "__main__":
    build()
