from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import re
from urllib.parse import urlparse
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, HRFlowable
)

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

BASE_DIR = Path(__file__).resolve().parent
FONT_CANDIDATES = [
    BASE_DIR / "fonts" / "NotoNaskhArabic-Regular.ttf",
    BASE_DIR / "NotoNaskhArabic-Regular.ttf",
]
FONT_PATH = next((x for x in FONT_CANDIDATES if x.exists()), None)
if FONT_PATH is None:
    raise FileNotFoundError("NotoNaskhArabic-Regular.ttf غير موجود. ضعه في جذر المشروع أو داخل fonts/")

pdfmetrics.registerFont(TTFont("TahlelArabic", str(FONT_PATH)))
pdfmetrics.registerFont(TTFont("TahlelArabicBold", str(FONT_PATH)))

# Brand palette
NAVY = colors.HexColor("#12263A")
TEAL = colors.HexColor("#0F766E")
MINT = colors.HexColor("#E8F5F2")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
SOFT = colors.HexColor("#F8FAFC")
GOOD_BG = colors.HexColor("#ECFDF5")
WARN_BG = colors.HexColor("#FFF7ED")
BAD_BG = colors.HexColor("#FEF2F2")
WHITE = colors.white


def rtl(text):
    text = str(text or "")
    if not arabic_reshaper or not get_display:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text), base_dir="R")
    except Exception:
        return text


def safe(text):
    return escape(str(text or ""))


def p(text, style, do_rtl=True):
    value = rtl(text) if do_rtl else str(text or "")
    return Paragraph(safe(value).replace("\n", "<br/>"), style)


def _host(url):
    try:
        return urlparse(url).netloc.replace("www.", "") or url
    except Exception:
        return url


def _analysis_text(analysis):
    if not analysis:
        return ""
    if isinstance(analysis, str):
        return analysis
    return str(analysis.get("ai_analysis") or analysis.get("message") or "")


def _split_sections(text):
    """Split common AI output headings such as '1 الملخص التنفيذي'."""
    lines = [x.strip() for x in str(text or "").splitlines() if x.strip()]
    sections, current_title, current = [], None, []
    heading_re = re.compile(r"^(?:#{1,4}\s*)?(\d{1,2})[\)\.\-:\s]+(.+)$")
    for line in lines:
        m = heading_re.match(line)
        if m and len(line) < 120:
            if current_title or current:
                sections.append((current_title or "التحليل", current))
            current_title = f"{m.group(1)}. {m.group(2).strip()}"
            current = []
        else:
            current.append(line)
    if current_title or current:
        sections.append((current_title or "التحليل التفصيلي", current))
    return sections


def _footer(canvas, doc):
    canvas.saveState()
    w, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18*mm, 14*mm, w-18*mm, 14*mm)
    canvas.setFont("TahlelArabic", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 8*mm, "TAHLEL")
    canvas.drawRightString(w-18*mm, 8*mm, f"{doc.page}")
    canvas.restoreState()


def build_pdf(data, analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=20*mm,
        title="تقرير تحليل الموقع - Tahlel", author="Tahlel",
    )

    base = getSampleStyleSheet()
    cover_brand = ParagraphStyle("CoverBrand", parent=base["Title"], fontName="TahlelArabicBold",
        fontSize=18, leading=24, alignment=TA_CENTER, textColor=TEAL)
    cover_title = ParagraphStyle("CoverTitle", parent=base["Title"], fontName="TahlelArabicBold",
        fontSize=28, leading=40, alignment=TA_CENTER, textColor=NAVY)
    cover_sub = ParagraphStyle("CoverSub", parent=base["BodyText"], fontName="TahlelArabic",
        fontSize=12, leading=20, alignment=TA_CENTER, textColor=MUTED)
    h1 = ParagraphStyle("H1", parent=base["Heading1"], fontName="TahlelArabicBold",
        fontSize=17, leading=26, alignment=TA_RIGHT, textColor=NAVY, spaceBefore=8, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=base["Heading2"], fontName="TahlelArabicBold",
        fontSize=13, leading=21, alignment=TA_RIGHT, textColor=TEAL, spaceBefore=8, spaceAfter=6)
    body = ParagraphStyle("Body", parent=base["BodyText"], fontName="TahlelArabic",
        fontSize=10.5, leading=18, alignment=TA_RIGHT, textColor=INK, spaceAfter=5)
    small = ParagraphStyle("Small", parent=body, fontSize=8.3, leading=13, textColor=MUTED)
    metric_big = ParagraphStyle("MetricBig", parent=body, fontName="TahlelArabicBold",
        fontSize=22, leading=26, alignment=TA_CENTER, textColor=NAVY)
    metric_label = ParagraphStyle("MetricLabel", parent=small, alignment=TA_CENTER)

    start_url = data.get("start_url", "")
    special = data.get("special_pages", {})
    labels = {
        "returns": "الاسترجاع والاستبدال", "shipping": "الشحن والتوصيل",
        "privacy": "الخصوصية", "complaints": "الشكاوى", "contact": "التواصل",
    }
    found = sum(bool(special.get(k)) for k in labels)
    coverage = round((found / len(labels)) * 100) if labels else 0
    pages_count = len(data.get("pages", []))

    story = []

    # Cover
    story += [Spacer(1, 30*mm), p("تحليل", cover_brand), Spacer(1, 6*mm),
              p("تقرير تحليل المتجر الإلكتروني", cover_title), Spacer(1, 6*mm),
              p(_host(start_url), cover_sub, do_rtl=False), Spacer(1, 20*mm)]
    cover_box = Table([[p("تقرير تنفيذي احترافي يوضح اكتمال السياسات، الفجوات التشغيلية، المخاطر، وفرص التحسين ذات الأولوية.", body)]], colWidths=[160*mm])
    cover_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SOFT), ("BOX", (0,0), (-1,-1), 0.8, LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 14), ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING", (0,0), (-1,-1), 14), ("BOTTOMPADDING", (0,0), (-1,-1), 14),
    ]))
    story += [cover_box, Spacer(1, 10*mm),
              p(f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d')}", cover_sub),
              Spacer(1, 12*mm), p("TAHLEL - Website Intelligence Report", small, do_rtl=False), PageBreak()]

    # Executive dashboard
    story += [p("الملخص التنفيذي", h1), HRFlowable(width="100%", thickness=1, color=LINE), Spacer(1, 5*mm)]
    metrics = [
        [p(f"{coverage}%", metric_big), p(str(found), metric_big), p(str(pages_count), metric_big)],
        [p("تغطية المحاور الأساسية", metric_label), p("محاور مكتشفة", metric_label), p("صفحات مفحوصة", metric_label)],
    ]
    mt = Table(metrics, colWidths=[53*mm, 53*mm, 53*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SOFT), ("BOX", (0,0), (-1,-1), 0.7, LINE),
        ("INNERGRID", (0,0), (-1,-1), 0.4, LINE), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story += [mt, Spacer(1, 7*mm), p("حالة المحاور الأساسية", h2)]

    rows = [[p("المحور", body), p("الحالة", body), p("المصدر", body)]]
    for key, label in labels.items():
        value = special.get(key)
        rows.append([p(label, body), p("موجود" if value else "غير موجود", body), p(value or "لم يتم العثور على صفحة", small, do_rtl=not bool(value))])
    table = Table(rows, colWidths=[47*mm, 27*mm, 85*mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,0), "TahlelArabicBold"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.45, LINE), ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8), ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
    ]
    for r, key in enumerate(labels, start=1):
        style.append(("BACKGROUND", (1,r), (1,r), GOOD_BG if special.get(key) else BAD_BG))
    table.setStyle(TableStyle(style))
    story += [table, Spacer(1, 8*mm)]

    missing = [label for key, label in labels.items() if not special.get(key)]
    if missing:
        note = "المحاور التي لم يعثر عليها الزاحف: " + "، ".join(missing) + ". يُنصح بمراجعتها قبل تسليم التقرير النهائي للعميل."
        box = Table([[p(note, body)]], colWidths=[159*mm])
        box.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),WARN_BG),("BOX",(0,0),(-1,-1),0.7,colors.HexColor("#FDBA74")),
                                  ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
                                  ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10)]))
        story += [box, Spacer(1, 5*mm)]

    # Commercial interpretation
    story += [p("قراءة سريعة", h2)]
    if coverage >= 80:
        quick = "تغطية السياسات الأساسية مرتفعة. تتركز القيمة التالية في تحسين وضوح الصياغة، توحيد البيانات، وتقليل الاحتكاك في رحلة العميل."
    elif coverage >= 60:
        quick = "تغطية السياسات الأساسية متوسطة. الأولوية هي استكمال المحاور غير المكتشفة ثم معالجة التناقضات التي قد تؤثر على الثقة والتحويل."
    else:
        quick = "تغطية السياسات الأساسية منخفضة. يوصى باستكمال الصفحات الأساسية قبل الانتقال إلى تحسينات تجربة الشراء المتقدمة."
    qbox = Table([[p(quick, body)]], colWidths=[159*mm])
    qbox.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),MINT),("BOX",(0,0),(-1,-1),0.7,TEAL),
                              ("TOPPADDING",(0,0),(-1,-1),11),("BOTTOMPADDING",(0,0),(-1,-1),11),
                              ("LEFTPADDING",(0,0),(-1,-1),11),("RIGHTPADDING",(0,0),(-1,-1),11)]))
    story += [qbox, Spacer(1, 5*mm)]

    # Detailed AI analysis
    text = _analysis_text(analysis)
    if text:
        story += [PageBreak(), p("التحليل والتوصيات", h1),
                  p("يعرض هذا القسم الملاحظات المستخرجة من الصفحات التي تم فحصها. يجب التحقق من أي نقطة تنظيمية أو قانونية قبل اعتمادها كاستشارة متخصصة.", small),
                  Spacer(1, 3*mm)]
        sections = _split_sections(text)
        if not sections:
            sections = [("التحليل التفصيلي", [text])]
        for title, lines in sections:
            content = []
            for line in lines:
                clean = re.sub(r"^[\-•*]+\s*", "", line).strip()
                if clean:
                    content.append(p(clean, body))
            if content:
                story.append(KeepTogether([p(title, h2)] + content[:2]))
                story.extend(content[2:])
                story.append(Spacer(1, 3*mm))

    # Closing page
    story += [Spacer(1, 5*mm), HRFlowable(width="100%", thickness=1, color=LINE), Spacer(1, 4*mm),
              p("ملاحظة منهجية", h2),
              p("يعتمد التقرير على المحتوى الذي استطاع الزاحف الوصول إليه وقت الفحص وعلى تحليل آلي للمحتوى. عدم اكتشاف صفحة لا يعني بالضرورة عدم وجودها؛ قد تكون محمية أو غير مرتبطة بوضوح داخل الموقع.", small)]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
