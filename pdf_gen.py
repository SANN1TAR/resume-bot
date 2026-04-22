# Генератор PDF резюме
# Вход: словарь с данными пользователя
# Выход: путь к готовому PDF файлу

import uuid
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", "DejaVuSans-Bold.ttf"))
        return "DejaVu", "DejaVu-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def generate_pdf(data: dict) -> str:
    font, font_bold = register_fonts()
    filename = f"/tmp/resume_{uuid.uuid4().hex}.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    style_name = ParagraphStyle(
        "Name", fontName=font_bold, fontSize=22,
        textColor=colors.HexColor("#1a1a2e"), spaceAfter=4
    )
    style_job = ParagraphStyle(
        "Job", fontName=font, fontSize=13,
        textColor=colors.HexColor("#e94560"), spaceAfter=2
    )
    style_contacts = ParagraphStyle(
        "Contacts", fontName=font, fontSize=10,
        textColor=colors.HexColor("#555555"), spaceAfter=12
    )
    style_section = ParagraphStyle(
        "Section", fontName=font_bold, fontSize=13,
        textColor=colors.HexColor("#1a1a2e"), spaceBefore=14, spaceAfter=4
    )
    style_body = ParagraphStyle(
        "Body", fontName=font, fontSize=11,
        textColor=colors.HexColor("#333333"), spaceAfter=4, leading=16
    )

    story = []

    story.append(Paragraph(data.get("name", ""), style_name))
    story.append(Paragraph(data.get("target_job", ""), style_job))
    story.append(Paragraph(
        f"{data.get('age', '')} лет  •  {data.get('city', '')}  •  "
        f"{data.get('phone', '')}  •  {data.get('email', '')}",
        style_contacts
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e94560")))

    sections = [
        ("О себе",      data.get("about", "")),
        ("Опыт работы", data.get("experience", "")),
        ("Навыки",      data.get("skills", "")),
        ("Образование", data.get("education", "")),
    ]

    for title, content in sections:
        if content:
            story.append(Paragraph(title, style_section))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 4))
            story.append(Paragraph(content, style_body))

    doc.build(story)
    return filename
