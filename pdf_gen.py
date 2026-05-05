import uuid
import tempfile
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, Table, TableStyle
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_fonts():
    search_paths = [
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf",              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",   "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"),
    ]
    for regular, bold in search_paths:
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", regular))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold))
            return "DejaVu", "DejaVu-Bold"
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"


def generate_pdf(data: dict) -> str:
    font, font_bold = register_fonts()
    filename = os.path.join(tempfile.gettempdir(), f"resume_{uuid.uuid4().hex}.pdf")

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=1.8 * cm, leftMargin=1.8 * cm,
        topMargin=1.5 * cm,   bottomMargin=1.5 * cm
    )

    ACCENT  = HexColor("#0D7377")   # teal
    PRIMARY = HexColor("#1E2D40")   # dark slate
    MUTED   = HexColor("#6B7280")   # gray
    DIVIDER = HexColor("#CBD5E0")   # light divider

    style_name = ParagraphStyle(
        "Name", fontName=font_bold, fontSize=24,
        textColor=PRIMARY, spaceAfter=4, leading=28
    )
    style_job = ParagraphStyle(
        "Job", fontName=font, fontSize=13,
        textColor=ACCENT, spaceAfter=4, leading=16
    )
    style_contacts = ParagraphStyle(
        "Contacts", fontName=font, fontSize=9.5,
        textColor=MUTED, spaceAfter=0, leading=13
    )
    style_section = ParagraphStyle(
        "Section", fontName=font_bold, fontSize=11,
        textColor=PRIMARY, spaceBefore=16, spaceAfter=4, leading=14
    )
    style_body = ParagraphStyle(
        "Body", fontName=font, fontSize=10.5,
        textColor=HexColor("#222222"), spaceAfter=4, leading=15
    )

    story = []

    # ── Header: name/job/contacts left | photo placeholder right ─────────────
    header_left = [
        Paragraph(data.get("name", ""), style_name),
        Paragraph(data.get("target_job", ""), style_job),
        Paragraph(
            f"{data.get('age', '')} лет  •  {data.get('city', '')}  •  "
            f"{data.get('phone', '')}  •  {data.get('email', '')}",
            style_contacts
        ),
    ]

    photo_box = Table(
        [["Фото"]],
        colWidths=[2.8 * cm],
        rowHeights=[3.3 * cm]
    )
    photo_box.setStyle(TableStyle([
        ("BOX",       (0, 0), (0, 0), 1,   DIVIDER),
        ("ALIGN",     (0, 0), (0, 0), "CENTER"),
        ("VALIGN",    (0, 0), (0, 0), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (0, 0), MUTED),
        ("FONTNAME",  (0, 0), (0, 0), font),
        ("FONTSIZE",  (0, 0), (0, 0), 9),
    ]))

    usable_w = A4[0] - 1.8 * cm - 1.8 * cm
    header_tbl = Table(
        [[header_left, photo_box]],
        colWidths=[usable_w - 3.2 * cm, 3.2 * cm]
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (1, 0), (1,  0),  "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (0,  0),  0),
        ("RIGHTPADDING",  (1, 0), (1,  0),  0),
    ]))

    story.append(header_tbl)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=2))

    # ── Sections (Russian market order) ──────────────────────────────────────
    sections = [
        ("ОПЫТ РАБОТЫ", data.get("experience", "")),
        ("ОБРАЗОВАНИЕ",  data.get("education", "")),
        ("НАВЫКИ",       data.get("skills", "")),
        ("О СЕБЕ",       data.get("about", "")),
    ]

    for title, content in sections:
        if content:
            story.append(Paragraph(title, style_section))
            story.append(HRFlowable(width="100%", thickness=0.5, color=DIVIDER, spaceAfter=4))
            story.append(Paragraph(content, style_body))

    doc.build(story)
    return filename
