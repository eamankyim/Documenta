import os
import fitz  # PyMuPDF

# ===== CONFIG =====
pdf_path = "Heritagio Blitzy AI Technical Specification.pdf"  # path to your PDF
output_dir = "heritagio_sections"  # folder to save HTML files
# Major headings to split by
section_titles = [
    "1. INTRODUCTION",
    "1.2 SYSTEM OVERVIEW",
    "1.3 SCOPE",
    "2. PRODUCT REQUIREMENTS",
    "3. TECHNOLOGY STACK",
    "4. PROCESS FLOWCHART",
]
# ==================

os.makedirs(output_dir, exist_ok=True)

# Open PDF
doc = fitz.open(pdf_path)

# Extract all text
full_text = ""
for page_num in range(len(doc)):
    full_text += doc[page_num].get_text("text") + "\n"

# Split into sections
sections = {}
current_section = None
for line in full_text.splitlines():
    if any(line.strip().startswith(title) for title in section_titles):
        current_section = line.strip()
        sections[current_section] = []
    if current_section:
        sections[current_section].append(line)

# Save each section as HTML
for title, lines in sections.items():
    safe_title = title.replace(" ", "_").replace(".", "_")
    section_path = os.path.join(output_dir, f"{safe_title}.html")
    section_text = "\n".join(lines)

    html_content = f"""<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    line-height: 1.6;
}}
h1 {{
    color: #333;
}}
pre {{
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>
<h1>{title}</h1>
<pre>{section_text}</pre>
</body>
</html>"""

    with open(section_path, "w", encoding="utf-8") as f:
        f.write(html_content)

print(f"✅ Done! HTML files saved in '{output_dir}'")
