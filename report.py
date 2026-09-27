from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = BASE_DIR / "NotoNaskhArabic-Regular.ttf"
FONT_BOLD_PATH = BASE_DIR / "NotoNaskhArabic-Regular.ttf"

pdfmetrics.registerFont(TTFont("TahlelArabic", str(FONT_PATH)))
pdfmetrics.registerFont(TTFont("TahlelArabicBold", str(FONT_BOLD_PATH)))


def rtl(text):
    """Shape Arabic and apply bidi ordering while leaving URLs/numbers readable."""
    text = str(text or "")
    if not arabic_reshaper or not get_display:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def p(text, style):
    return Paragraph(escape(rtl(text)).replace("\n", "<br/>"), style)


def build_pdf(data, analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=42,
        bottomMargin=42,
        title="تقرير تحليل الموقع - Tahlel",
        author="Tahlel",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TahlelTitle", parent=styles["Title"], fontName="TahlelArabicBold",
        fontSize=22, leading=30, alignment=TA_RIGHT, spaceAfter=8,
    )
    heading = ParagraphStyle(
        "TahlelHeading", parent=styles["Heading2"], fontName="TahlelArabicBold",
        fontSize=14, leading=22, alignment=TA_RIGHT, spaceBefore=12, spaceAfter=8,
    )
    body = ParagraphStyle(
        "TahlelBody", parent=styles["BodyText"], fontName="TahlelArabic",
        fontSize=10.5, leading=18, alignment=TA_RIGHT, spaceAfter=5,
    )
    small = ParagraphStyle(
        "TahlelSmall", parent=body, fontSize=8.5, leading=14,
    )

    story = [
        p("تقرير تحليل الموقع", title),
        p(data.get("start_url", ""), small),
        Spacer(1, 14),
        p("ملخص الزحف", heading),
    ]

    labels = {
        "returns": "الاسترجاع والاستبدال",
        "shipping": "الشحن والتوصيل",
        "privacy": "الخصوصية",
        "complaints": "الشكاوى",
        "contact": "التواصل",
    }

    rows = [[p("البند", body), p("النتيجة", body), p("الرابط", body)]]
    for key, label in labels.items():
        value = data.get("special_pages", {}).get(key)
        rows.append([
            p(label, body),
            p("موجود" if value else "غير موجود", body),
            p(value or "—", small),
        ])

    table = Table(rows, colWidths=[120, 85, 255], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [table, Spacer(1, 16)]

    if analysis:
        story.append(p("تحليل الذكاء الاصطناعي", heading))
        for value in analysis.values():
            if value:
                story.append(p(str(value), body))
                story.append(Spacer(1, 7))

    doc.build(story)
    return buffer.getvalue()
