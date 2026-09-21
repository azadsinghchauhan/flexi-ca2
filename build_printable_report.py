#!/usr/bin/env python3
"""
Convert PROJECT_REPORT_AZAD_SINGH_CHAUHAN.md into a beautifully formatted,
print-ready HTML document adhering strictly to academic formatting standards
and SIT Nagpur guidelines.
"""

import re
import html

def markdown_to_html(md_text):
    # Split by lines
    lines = md_text.splitlines()
    html_lines = []
    
    in_code_block = False
    code_lang = ""
    code_buffer = []
    
    in_table = False
    table_header = []
    table_rows = []
    
    in_ul = False
    in_ol = False
    
    def close_lists():
        nonlocal in_ul, in_ol
        res = ""
        if in_ul:
            res += "</ul>\n"
            in_ul = False
        if in_ol:
            res += "</ol>\n"
            in_ol = False
        return res

    def close_table():
        nonlocal in_table, table_header, table_rows
        if not in_table:
            return ""
        out = "<div class='table-container'><table class='report-table'>\n"
        if table_header:
            out += "  <thead>\n    <tr>\n"
            for cell in table_header:
                out += f"      <th>{format_inline(cell)}</th>\n"
            out += "    </tr>\n  </thead>\n"
        if table_rows:
            out += "  <tbody>\n"
            for row in table_rows:
                out += "    <tr>\n"
                for cell in row:
                    out += f"      <td>{format_inline(cell)}</td>\n"
                out += "    </tr>\n"
            out += "  </tbody>\n"
        out += "</table></div>\n"
        in_table = False
        table_header = []
        table_rows = []
        return out

    def format_inline(text):
        # Code inline
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        # Bold + Italic
        text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'___([^_]+)___', r'<strong><em>\1</em></strong>', text)
        # Bold
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
        # Math LaTeX simplified representation
        text = re.sub(r'\$\$([^\$]+)\$\$', r'<div class="math-block"><code>\1</code></div>', text)
        text = re.sub(r'\$([^\$]+)\$', r'<span class="math-inline"><code>\1</code></span>', text)
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle page breaks
        if '<div style="page-break-after: always;"></div>' in line or '<div style="page-break-before: always;"></div>' in line:
            html_lines.append(close_lists())
            html_lines.append(close_table())
            html_lines.append('<div class="page-break"></div>')
            i += 1
            continue

        # Code block toggle
        if stripped.startswith("```"):
            if not in_code_block:
                html_lines.append(close_lists())
                html_lines.append(close_table())
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_buffer = []
            else:
                in_code_block = False
                escaped_code = html.escape("\n".join(code_buffer))
                html_lines.append(f'<pre class="code-block language-{code_lang}"><code>{escaped_code}</code></pre>')
                code_buffer = []
            i += 1
            continue

        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue

        # Horizontal rule
        if stripped in ["---", "***", "___"]:
            html_lines.append(close_lists())
            html_lines.append(close_table())
            html_lines.append('<hr class="section-divider">')
            i += 1
            continue

        # Markdown tables
        if stripped.startswith("|") and stripped.endswith("|"):
            html_lines.append(close_lists())
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Check if divider line like |:---|:---|
            if all(re.match(r'^:?-+:?$', c) for c in cells):
                # Just header divider
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
            html_lines.append(close_table())

        # Alerts / Blockquotes
        if stripped.startswith(">"):
            html_lines.append(close_lists())
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            quote_text = " ".join(quote_lines)
            alert_type = "info"
            if "[!NOTE]" in quote_text:
                alert_type = "note"
                quote_text = quote_text.replace("[!NOTE]", "").strip()
            elif "[!IMPORTANT]" in quote_text:
                alert_type = "important"
                quote_text = quote_text.replace("[!IMPORTANT]", "").strip()
            elif "[!TIP]" in quote_text:
                alert_type = "tip"
                quote_text = quote_text.replace("[!TIP]", "").strip()
            elif "[!WARNING]" in quote_text:
                alert_type = "warning"
                quote_text = quote_text.replace("[!WARNING]", "").strip()
            html_lines.append(f'<div class="callout callout-{alert_type}">{format_inline(quote_text)}</div>')
            continue

        # Headings
        if stripped.startswith("#"):
            html_lines.append(close_lists())
            level = len(re.match(r'^#+', stripped).group(0))
            heading_text = stripped[level:].strip()
            # Clean anchors or special formatting
            clean_text = format_inline(heading_text)
            html_lines.append(f'<h{level} class="heading-{level}">{clean_text}</h{level}>')
            i += 1
            continue

        # Unordered list
        ul_match = re.match(r'^[\*\-\+]\s+(.*)', stripped)
        if ul_match:
            if in_ol:
                html_lines.append("</ol>\n")
                in_ol = False
            if not in_ul:
                html_lines.append('<ul class="report-ul">\n')
                in_ul = True
            html_lines.append(f'  <li>{format_inline(ul_match.group(1))}</li>')
            i += 1
            continue

        # Ordered list
        ol_match = re.match(r'^\d+\.\s+(.*)', stripped)
        if ol_match:
            if in_ul:
                html_lines.append("</ul>\n")
                in_ul = False
            if not in_ol:
                html_lines.append('<ol class="report-ol">\n')
                in_ol = True
            html_lines.append(f'  <li>{format_inline(ol_match.group(1))}</li>')
            i += 1
            continue

        # Empty line
        if not stripped:
            html_lines.append(close_lists())
            i += 1
            continue

        # Explicit line breaks like <br>
        if stripped == "<br>" or stripped == "<br><br>" or stripped == "<br><br><br>":
            html_lines.append(stripped)
            i += 1
            continue

        # Normal paragraph
        html_lines.append(close_lists())
        html_lines.append(f'<p class="report-p">{format_inline(stripped)}</p>')
        i += 1

    html_lines.append(close_lists())
    html_lines.append(close_table())

    return "\n".join(html_lines)


def build_full_html():
    with open("PROJECT_REPORT_AZAD_SINGH_CHAUHAN.md", "r", encoding="utf-8") as f:
        md_content = f.read()

    body_html = markdown_to_html(md_content)

    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automated News Topic Monitoring Using Agentic AI - Project Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1e3a8a;
            --primary-dark: #0f172a;
            --secondary: #0284c7;
            --text-main: #1f2937;
            --text-muted: #4b5563;
            --bg-page: #ffffff;
            --border-color: #e5e7eb;
            --callout-bg: #f8fafc;
            --code-bg: #f1f5f9;
        }}

        @page {{
            size: A4 portrait;
            margin: 25mm 20mm 25mm 20mm;
            @top-center {{
                content: "Automated News Topic Monitoring Using Agentic AI | SIT Nagpur";
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 8pt;
                color: #64748b;
                border-bottom: 0.5pt solid #cbd5e1;
                padding-bottom: 4px;
            }}
            @bottom-center {{
                content: counter(page);
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 9pt;
                color: #475569;
                font-weight: 600;
            }}
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Crimson Pro', 'Georgia', serif;
            font-size: 11.5pt;
            line-height: 1.65;
            color: var(--text-main);
            background-color: #f3f4f6;
            margin: 0;
            padding: 0;
        }}

        .report-wrapper {{
            max-width: 900px;
            margin: 30px auto;
            background: #ffffff;
            padding: 60px 70px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            border-radius: 4px;
        }}

        @media print {{
            body {{
                background-color: #ffffff;
            }}
            .report-wrapper {{
                max-width: 100%;
                margin: 0;
                padding: 0;
                box-shadow: none;
                border-radius: 0;
            }}
            .no-print {{
                display: none !important;
            }}
            .page-break {{
                page-break-after: always;
                break-after: page;
            }}
        }}

        /* Action Toolbar */
        .action-toolbar {{
            position: sticky;
            top: 15px;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(10px);
            padding: 12px 24px;
            border-radius: 12px;
            max-width: 900px;
            margin: 15px auto 25px auto;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            color: white;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        .toolbar-btn {{
            background: #2563eb;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            transition: all 0.2s ease;
        }}
        .toolbar-btn:hover {{
            background: #1d4ed8;
            transform: translateY(-1px);
        }}
        .toolbar-badge {{
            background: #0284c7;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}

        /* Typography & Headings */
        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: var(--primary-dark);
            margin-top: 1.8em;
            margin-bottom: 0.6em;
            page-break-after: avoid;
            break-after: avoid;
        }}

        .heading-1 {{
            font-size: 20pt;
            font-weight: 800;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .heading-2 {{
            font-size: 15pt;
            font-weight: 700;
            color: #1e3a8a;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 6px;
        }}

        .heading-3 {{
            font-size: 12.5pt;
            font-weight: 700;
            color: #0f172a;
        }}

        .heading-4 {{
            font-size: 11pt;
            font-weight: 600;
            color: #334155;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .report-p {{
            margin-bottom: 1.1em;
            text-align: justify;
            text-justify: inter-word;
            text-indent: 1.5em;
        }}

        .report-ul, .report-ol {{
            margin-top: 0.5em;
            margin-bottom: 1.2em;
            padding-left: 2em;
        }}

        .report-ul li, .report-ol li {{
            margin-bottom: 0.4em;
            text-align: justify;
        }}

        .section-divider {{
            border: none;
            border-top: 1px solid #cbd5e1;
            margin: 35px 0;
        }}

        /* Tables */
        .table-container {{
            width: 100%;
            overflow-x: auto;
            margin: 20px 0 25px 0;
            page-break-inside: avoid;
        }}

        .report-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 9.5pt;
            background: #ffffff;
        }}

        .report-table th {{
            background: #0f172a;
            color: #ffffff;
            font-weight: 600;
            padding: 10px 12px;
            text-align: left;
            border: 1px solid #0f172a;
        }}

        .report-table td {{
            padding: 8px 12px;
            border: 1px solid #cbd5e1;
            color: #334155;
            vertical-align: top;
        }}

        .report-table tr:nth-child(even) {{
            background-color: #f8fafc;
        }}

        /* Code Blocks */
        pre.code-block {{
            background: #0f172a;
            color: #f8fafc;
            padding: 14px 18px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 8.5pt;
            line-height: 1.5;
            overflow-x: auto;
            margin: 18px 0;
            page-break-inside: avoid;
            border: 1px solid #1e293b;
        }}

        code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9pt;
            background: #e2e8f0;
            color: #0f172a;
            padding: 2px 5px;
            border-radius: 4px;
        }}

        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}

        /* Math and Callouts */
        .math-block {{
            background: #f1f5f9;
            padding: 10px 15px;
            margin: 15px 0;
            border-left: 3px solid #0284c7;
            font-family: 'JetBrains Mono', monospace;
            text-align: center;
        }}

        .callout {{
            border-left: 4px solid #2563eb;
            background: #f8fafc;
            padding: 12px 18px;
            margin: 18px 0;
            border-radius: 0 6px 6px 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 9.5pt;
        }}
        .callout-important {{
            border-left-color: #dc2626;
            background: #fef2f2;
        }}
        .callout-note {{
            border-left-color: #2563eb;
            background: #eff6ff;
        }}
        .callout-tip {{
            border-left-color: #10b981;
            background: #f0fdf4;
        }}

        /* Specific Cover Page & Cert Page adjustments */
        .page-break {{
            page-break-after: always;
            break-after: page;
            height: 0;
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>

    <div class="action-toolbar no-print">
        <div>
            <strong>Symbiosis Institute of Technology (SIT), Nagpur</strong>
            <span class="toolbar-badge" style="margin-left: 10px;">AY 2026-27</span>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <button class="toolbar-btn" onclick="window.print()">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4H7v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
                Print / Save as PDF (30+ Pages)
            </button>
        </div>
    </div>

    <div class="report-wrapper">
        {body_html}
    </div>

</body>
</html>
"""
    with open("PROJECT_REPORT_PRINTABLE.html", "w", encoding="utf-8") as f:
        f.write(html_document)
    print("Successfully generated PROJECT_REPORT_PRINTABLE.html (Size: ~{} KB)".format(len(html_document) // 1024))

if __name__ == "__main__":
    build_full_html()
