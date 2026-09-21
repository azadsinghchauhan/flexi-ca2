#!/usr/bin/env python3
"""
Generate a professional, publication-quality academic PDF report from the project markdown
using ReportLab, matching the SIT Nagpur formatting standard.
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        # Don't draw header/footer on cover page (page 1)
        if self._pageNumber == 1:
            return
        
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Running header
        self.drawString(54, 842 - 36, "Automated News Topic Monitoring Using Agentic AI | SIT Nagpur")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 842 - 42, 595 - 54, 842 - 42)
        
        # Footer page number
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(595 - 54, 36, page_text)
        self.drawString(54, 36, "Department of Computer Science and Engineering - AY 2026-27")
        self.line(54, 46, 595 - 54, 46)
        
        self.restoreState()


def build_pdf():
    pdf_filename = "PROJECT_REPORT_AZAD_SINGH_CHAUHAN.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Center
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=25
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6,
        alignment=4 # Justified
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=6
    )

    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=body_style,
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#eff6ff"),
        borderColor=colors.HexColor("#2563eb"),
        borderWidth=1,
        borderPadding=8,
        spaceBefore=8,
        spaceAfter=8
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1f2937")
    )

    with open("PROJECT_REPORT_AZAD_SINGH_CHAUHAN.md", "r", encoding="utf-8") as f:
        md_text = f.read()

    lines = md_text.splitlines()
    story = []

    def clean_md(text):
        if not text:
            return ""

        # Step 1: Protect inline code snippets
        code_store = {}
        def save_code(m):
            key = f"__CODE_SNIP_{len(code_store)}__"
            code_content = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            code_store[key] = f'<font face="Courier" color="#1e3a8a">{code_content}</font>'
            return key

        text = re.sub(r'`([^`]+)`', save_code, text)

        # Step 2: Escape raw HTML chars in text (safe for XML)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Step 3: Math formatting (remove raw LaTeX formatting for clean PDF display)
        text = re.sub(r'\$\$([^\$]+)\$\$', r'<b>[\1]</b>', text)
        text = re.sub(r'\$([^\$]+)\$', r'<b>\1</b>', text)

        # Step 4: Bold and Italics
        text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<b><i>\1</i></b>', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
        # Only italicize standalone underscores with spaces or word boundaries
        text = re.sub(r'(?<=\s)_([^_]+)_(?=\s|[.,;:!?]|$)', r'<i>\1</i>', text)

        # Step 5: Restore inline code snippets
        for key, code_html in code_store.items():
            text = text.replace(key, code_html)

        # Step 6: Fix standard line breaks
        text = text.replace("&lt;br&gt;", "<br/>").replace("&lt;br/&gt;", "<br/>")

        return text

    in_code = False
    code_lines = []
    in_table = False
    table_header = []
    table_rows = []

    def flush_table():
        nonlocal in_table, table_header, table_rows
        if not in_table:
            return
        
        # Build table data with Paragraph flowables to wrap nicely
        num_cols = len(table_header) if table_header else (len(table_rows[0]) if table_rows else 1)
        # Printable width is 595 - 108 = 487 pt
        col_w = 487.0 / num_cols
        
        data = []
        if table_header:
            data.append([Paragraph(clean_md(c), table_header_style) for c in table_header])
        for row in table_rows:
            # Pad row if uneven
            padded = row + [""] * (num_cols - len(row))
            data.append([Paragraph(clean_md(c), table_cell_style) for c in padded[:num_cols]])

        t = Table(data, colWidths=[col_w] * num_cols)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 4))
        story.append(t)
        story.append(Spacer(1, 8))
        in_table = False
        table_header = []
        table_rows = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check page break
        if '<div style="page-break-after: always;"></div>' in line or '<div style="page-break-before: always;"></div>' in line:
            flush_table()
            story.append(PageBreak())
            i += 1
            continue

        # Check code block
        if stripped.startswith("```"):
            if not in_code:
                flush_table()
                in_code = True
                code_lines = []
            else:
                in_code = False
                code_text = "\n".join(code_lines)
                # Keep code snippets reasonable in size
                if len(code_lines) > 40:
                    code_text = "\n".join(code_lines[:40]) + "\n... [truncated for print layout] ..."
                story.append(Preformatted(code_text, code_style))
                code_lines = []
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Check horizontal rule
        if stripped in ["---", "***", "___"]:
            flush_table()
            story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1"), spaceBefore=10, spaceAfter=10))
            i += 1
            continue

        # Check table
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if all(re.match(r'^:?-+:?$', c) for c in cells):
                i += 1
                continue
            if not in_table:
                in_table = True
                table_header = cells
            else:
                table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            flush_table()

        # Blockquote / Alert
        if stripped.startswith(">"):
            quote_text = stripped[1:].strip()
            quote_text = re.sub(r'\[!(NOTE|IMPORTANT|TIP|WARNING)\]', r'<b>[\1]</b>', quote_text)
            story.append(Paragraph(clean_md(quote_text), callout_style))
            i += 1
            continue

        # Headings
        if stripped.startswith("#"):
            level = len(re.match(r'^#+', stripped).group(0))
            text = stripped[level:].strip()
            if level == 1:
                story.append(Paragraph(clean_md(text), h1_style))
            elif level == 2:
                story.append(Paragraph(clean_md(text), h2_style))
            else:
                story.append(Paragraph(clean_md(text), h3_style))
            i += 1
            continue

        # Bullet list
        ul_match = re.match(r'^[\*\-\+]\s+(.*)', stripped)
        if ul_match:
            story.append(Paragraph(f"&bull; {clean_md(ul_match.group(1))}", bullet_style))
            i += 1
            continue

        # Numbered list
        ol_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if ol_match:
            story.append(Paragraph(f"<b>{ol_match.group(1)}.</b> {clean_md(ol_match.group(2))}", bullet_style))
            i += 1
            continue

        # Empty lines / spacing
        if not stripped:
            i += 1
            continue

        # Normal paragraph
        story.append(Paragraph(clean_md(stripped), body_style))
        i += 1

    flush_table()

    # Build the document using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {pdf_filename}!")

if __name__ == "__main__":
    build_pdf()
