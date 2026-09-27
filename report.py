from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

def build_pdf(data, analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleAr", parent=styles["Title"], fontSize=20, leading=26, alignment=TA_RIGHT)
    body = ParagraphStyle("BodyAr", parent=styles["BodyText"], fontSize=10, leading=16, alignment=TA_RIGHT)
    story = [Paragraph("تقرير تحليل الموقع", title), Spacer(1, 8), Paragraph(data["start_url"], body), Spacer(1, 16), Paragraph("ملخص الزحف", styles["Heading2"])]
    labels = {"returns":"الاسترجاع","shipping":"الشحن","privacy":"الخصوصية","complaints":"الشكاوى","contact":"التواصل"}
    rows = [["البند", "النتيجة", "الرابط"]]
    for key, label in labels.items():
        value = data["special_pages"].get(key)
        rows.append([label, "موجود" if value else "غير موجود", value or "—"])
    table = Table(rows, colWidths=[100,100,260])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#222222")), ("TEXTCOLOR",(0,0),(-1,0),colors.white), ("GRID",(0,0),(-1,-1),0.5,colors.grey), ("ALIGN",(0,0),(-1,-1),"RIGHT"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("BOTTOMPADDING",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),8)]))
    story += [table, Spacer(1,18)]
    if analysis:
        story.append(Paragraph("تحليل الذكاء الاصطناعي", styles["Heading2"]))
        for value in analysis.values():
            story += [Paragraph(str(value).replace("\n","<br/>"), body), Spacer(1,10)]
    doc.build(story)
    return buffer.getvalue()
