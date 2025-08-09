import os
import fitz  # PyMuPDF
from pathlib import Path
import re
import base64
from io import BytesIO
from PIL import Image
import json

class PDFToHTMLConverter:
    def __init__(self, pdf_path, output_file):
        self.pdf_path = pdf_path
        self.output_file = output_file
        self.doc = fitz.open(pdf_path)
        self.images = []
        self.tables = []
        self.sections = {}
        self.flowcharts = []
        
    def extract_images(self):
        """Extract all images from PDF and convert to base64.
        Also compute hashes and transparency to detect and flag repeated watermarks.
        """
        import hashlib
        print("Extracting images and diagrams...")
        temp_images = []
        hash_counts = {}
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_area = float(page.rect.width * page.rect.height) if page.rect else 1.0
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    # Extract image data
                    base_image = self.doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Hash for duplicate detection
                    sha1 = hashlib.sha1(image_bytes).hexdigest()
                    hash_counts[sha1] = hash_counts.get(sha1, 0) + 1
                    
                    # Convert to base64 for embedding
                    image_b64 = base64.b64encode(image_bytes).decode()
                    
                    # Get image rectangles and rough area ratio
                    image_rects = page.get_image_rects(xref)
                    area_ratio = 0.0
                    width = height = 0.0
                    if image_rects:
                        rect = image_rects[0]
                        width = rect.width
                        height = rect.height
                        try:
                            area_ratio = float((width * height) / page_area) if page_area else 0.0
                        except Exception:
                            area_ratio = 0.0
                    
                    # Determine if this is a diagram based on size
                    is_diagram = True if (width > 400 or height > 300) else False

                    # Transparency (alpha) heuristic
                    alpha_mean = None
                    try:
                        with Image.open(BytesIO(image_bytes)) as pil_img:
                            if pil_img.mode != 'RGBA':
                                pil_img = pil_img.convert('RGBA')
                            alpha = pil_img.split()[-1]
                            # Mean alpha (0 transparent, 255 opaque)
                            alpha_mean = float(sum(alpha.getdata())) / (alpha.width * alpha.height)
                    except Exception:
                        alpha_mean = None
                    
                    temp_images.append({
                        'page': page_num,
                        'index': img_index,
                        'data': f"data:image/{image_ext};base64,{image_b64}",
                        'ext': image_ext,
                        'rects': image_rects,
                        'xref': xref,
                        'width': width,
                        'height': height,
                        'area_ratio': area_ratio,
                        'alpha_mean': alpha_mean,
                        'sha1': sha1,
                        'is_diagram': is_diagram,
                        'is_watermark': False,
                    })
                except Exception as e:
                    print(f"Error extracting image {img_index} from page {page_num}: {e}")

        # Post-process to flag likely watermarks: repeated hash across many pages + transparency/area pattern
        num_pages = len(self.doc)
        for img in temp_images:
            repeat = hash_counts.get(img['sha1'], 0)
            # Repetition threshold: appears on >= 3 pages and >= 30% of pages if doc is long
            repeated_enough = repeat >= 3 and (repeat >= max(3, int(0.3 * num_pages)))
            transparent_like = img['alpha_mean'] is not None and img['alpha_mean'] < 220
            medium_area = 0.03 <= img['area_ratio'] <= 0.6  # many diagonal watermarks occupy noticeable area, but not full-page
            if repeated_enough and (transparent_like or medium_area):
                img['is_watermark'] = True

        # Keep all images but mark watermarks; consumer will skip them
        self.images = temp_images
    
    def detect_tables_advanced(self):
        """Advanced table detection based on the document structure"""
        print("Detecting tables with advanced pattern recognition...")
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # Get text blocks with position information
            text_dict = page.get_text("dict")
            blocks = text_dict["blocks"]
            
            # Look for table patterns
            self.find_stakeholder_tables(blocks, page_num)
            self.find_technical_tables(blocks, page_num)
            self.find_requirements_tables(blocks, page_num)
            # Grid/table drawn by lines
            try:
                self._detect_tables_from_drawing_lines(page, page_num)
            except Exception as e:
                print(f"Grid table detection error on page {page_num}: {e}")
            # Fallback: text-grid reconstruction
            try:
                self._detect_tables_from_text_grid(page, page_num)
            except Exception as e:
                print(f"Text-grid table detection error on page {page_num}: {e}")

    def _detect_tables_from_drawing_lines(self, page, page_num: int):
        """Detect tables formed by drawing commands (grid lines) and extract cell text.
        Heuristic: collect horizontal/vertical lines, cluster to grid, read text per cell.
        """
        drawings = page.get_drawings()
        horizontals = []
        verticals = []
        for d in drawings:
            items = d.get('items') or []
            for it in items:
                # Expect it like [path, color, fill, even_odd, width, lineCap, dashes]
                if not isinstance(it, (list, tuple)) or len(it) == 0:
                    continue
                path = it[0]
                if not isinstance(path, list):
                    continue
                for cmd in path:
                    if not isinstance(cmd, (list, tuple)) or len(cmd) < 2:
                        continue
                    op = cmd[0]
                    pts = cmd[1]
                    if not isinstance(op, str):
                        continue
                    if not isinstance(pts, (list, tuple)) or len(pts) < 4:
                        continue
                    # Extract endpoints safely
                    try:
                        x0 = float(pts[0]); y0 = float(pts[1]); x1 = float(pts[-2]); y1 = float(pts[-1])
                    except Exception:
                        continue
                    if abs(y1 - y0) < 1.0 and abs(x1 - x0) > 10:
                        horizontals.append((min(x0, x1), y0, max(x0, x1), y1))
                    elif abs(x1 - x0) < 1.0 and abs(y1 - y0) > 10:
                        verticals.append((x0, min(y0, y1), x1, max(y0, y1)))

        if len(horizontals) < 2 or len(verticals) < 2:
            return

        def cluster(vals, tol=3.0):
            vals = sorted(vals)
            clusters = []
            for v in vals:
                if not clusters or abs(v - clusters[-1][-1]) > tol:
                    clusters.append([v, v])
                else:
                    clusters[-1][1] = v
            centers = [(a + b) / 2.0 for a, b in clusters]
            return centers

        xs = cluster([x0 for (x0, _, x1, _) in horizontals] + [x0 for (x0, _, _, _) in verticals] + [x1 for (_, _, x1, _) in horizontals])
        ys = cluster([y0 for (_, y0, _, y1) in verticals] + [y0 for (_, y0, _, _) in horizontals] + [y1 for (_, _, _, y1) in verticals])
        if len(xs) < 2 or len(ys) < 2:
            return
        xs.sort(); ys.sort()

        headers = None
        rows = []
        for r in range(len(ys) - 1):
            row_cells = []
            for c in range(len(xs) - 1):
                rect = fitz.Rect(xs[c] + 1, ys[r] + 1, xs[c + 1] - 1, ys[r + 1] - 1)
                try:
                    txt = page.get_textbox(rect).strip()
                except Exception:
                    txt = ""
                txt = self._clean_text_fragments(txt)
                row_cells.append(txt)
            if headers is None and any(cell for cell in row_cells):
                headers = [cell if cell else f"Col {i+1}" for i, cell in enumerate(row_cells)]
            else:
                rows.append(row_cells)

        if headers and rows:
            self.tables.append({
                'page': page_num,
                'data': [headers] + rows,
                'type': 'grid',
                'title': 'Detected Table'
            })

    def _detect_tables_from_text_grid(self, page, page_num: int):
        """Fallback: reconstruct table-like grids by clustering span positions across the page.
        Builds rows by similar y, then splits cells by large x gaps.
        """
        text_dict = page.get_text("dict")
        span_rows = []  # list of (y_top, x_left, text)
        for block in text_dict.get('blocks', []):
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    txt = span.get('text', '').strip()
                    if not txt:
                        continue
                    bbox = span.get('bbox')
                    if not bbox or len(bbox) < 2:
                        continue
                    try:
                        x0 = float(bbox[0]); y0 = float(bbox[1])
                    except Exception:
                        continue
                    span_rows.append((y0, x0, txt))
        if not span_rows:
            return

        # Cluster by y within tolerance
        span_rows.sort(key=lambda t: (t[0], t[1]))
        rows = []
        tol_y = 3.0
        current = []
        last_y = None
        for y0, x0, txt in span_rows:
            if last_y is None or abs(y0 - last_y) <= tol_y:
                current.append((x0, txt))
                last_y = y0 if last_y is None else (last_y + y0) / 2.0
            else:
                rows.append(current)
                current = [(x0, txt)]
                last_y = y0
        if current:
            rows.append(current)

        # Build cells by splitting on x gaps
        built_rows = []
        gap_threshold = 25.0
        for spans in rows:
            if not spans:
                continue
            spans.sort(key=lambda t: t[0])
            cells = []
            buf = []
            prev_x = None
            for x, txt in spans:
                if prev_x is not None and (x - prev_x) > gap_threshold and buf:
                    cells.append(' '.join(buf).strip())
                    buf = [txt]
                else:
                    buf.append(txt)
                prev_x = x
            if buf:
                cells.append(' '.join(buf).strip())
            built_rows.append(cells)

        # Determine dominant column count
        counts = {}
        for r in built_rows:
            counts[len(r)] = counts.get(len(r), 0) + 1
        # Only consider as table if we see at least 3 rows with the same >=3 column count
        if not counts:
            return
        col_count, freq = max(counts.items(), key=lambda kv: kv[1])
        if col_count < 3 or freq < 3:
            return

        # Build table data with that column count (pad/truncate as needed)
        filtered = []
        for r in built_rows:
            if len(r) < col_count:
                r = r + [''] * (col_count - len(r))
            elif len(r) > col_count:
                r = r[:col_count]
            filtered.append([self._clean_text_fragments(c) for c in r])

        # Determine header row (first non-empty)
        headers = None
        data_rows = []
        for r in filtered:
            if headers is None and any(c for c in r):
                headers = [c if c else f"Col {i+1}" for i, c in enumerate(r)]
            else:
                data_rows.append(r)

        if headers and data_rows:
            self.tables.append({
                'page': page_num,
                'data': [headers] + data_rows,
                'type': 'grid',
                'title': 'Detected Table'
            })
    
    def find_stakeholder_tables(self, blocks, page_num):
        """Find stakeholder category tables"""
        table_data = []
        collecting_table = False
        header_y0 = None
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    first_span_y = None
                    for span in line["spans"]:
                        line_text += span["text"].strip() + " "
                        if first_span_y is None and span.get("bbox"):
                            try:
                                first_span_y = float(span["bbox"][1])
                            except Exception:
                                first_span_y = None
                    
                    line_text = line_text.strip()
                    
                    # Detect table headers
                    if any(header in line_text for header in ["Stakeholder Category", "Primary Users", "Secondary Users"]):
                        collecting_table = True
                        header_y0 = first_span_y
                        if len(line_text.split()) >= 2:  # Multi-column header
                            table_data.append(["Stakeholder Category", "Primary Users", "Secondary Users"])
                    
                    # Collect table rows
                    elif collecting_table and line_text:
                        if any(category in line_text for category in ["Cultural Producers", "Government Partners", "End Consumers", "Technology Partners"]):
                            # This is a table row - try to split it intelligently
                            parts = self.split_table_row(line_text)
                            if len(parts) >= 2:
                                table_data.append(parts)
                        elif line_text and not any(stopper in line_text.lower() for stopper in ["expected", "business", "impact"]):
                            continue
                        else:
                            collecting_table = False
        
        if table_data and len(table_data) > 1:
            self.tables.append({
                'page': page_num,
                'data': table_data,
                'type': 'stakeholder',
                'title': 'Key Stakeholders and Users',
                'y0': header_y0
            })
    
    def find_technical_tables(self, blocks, page_num):
        """Find technical specification tables"""
        table_data = []
        collecting_table = False
        header_y0 = None
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    first_span_y = None
                    for span in line["spans"]:
                        line_text += span["text"].strip() + " "
                        if first_span_y is None and span.get("bbox"):
                            try:
                                first_span_y = float(span["bbox"][1])
                            except Exception:
                                first_span_y = None
                    
                    line_text = line_text.strip()
                    
                    # Look for dependency tables
                    if any(header in line_text for header in ["Dependency Type", "Requirements"]):
                        collecting_table = True
                        header_y0 = first_span_y
                        table_data.append(["Dependency Type", "Requirements"])
                    
                    # Look for functional requirements tables
                    elif any(header in line_text for header in ["Requirement ID", "Description", "Acceptance Criteria"]):
                        collecting_table = True
                        header_y0 = first_span_y
                        if "Priority" in line_text and "Complexity" in line_text:
                            table_data.append(["Requirement ID", "Description", "Acceptance Criteria", "Priority", "Complexity"])
                        else:
                            table_data.append(["Requirement ID", "Description", "Acceptance Criteria"])
                    
                    # Look for objectives table
                    elif any(header in line_text for header in ["Objective Category", "Target Metric", "Timeline"]):
                        collecting_table = True
                        header_y0 = first_span_y
                        table_data.append(["Objective Category", "Target Metric", "Timeline"])
                    
                    # Collect table rows
                    elif collecting_table and line_text:
                        if self.is_table_row(line_text):
                            parts = self.split_table_row(line_text)
                            if len(parts) >= 2:
                                table_data.append(parts)
                        elif not line_text or self.is_section_break(line_text):
                            if table_data and len(table_data) > 1:
                                self.tables.append({
                                    'page': page_num,
                                    'data': table_data,
                                    'type': 'technical',
                                    'title': 'Technical Specifications'
                                })
                            collecting_table = False
                            table_data = []
        
        # Add final table if exists
        if table_data and len(table_data) > 1:
            self.tables.append({
                'page': page_num,
                'data': table_data,
                'type': 'technical',
                'title': 'Technical Specifications',
                'y0': header_y0
            })
    
    def find_requirements_tables(self, blocks, page_num):
        """Find requirements and specifications tables"""
        # This will be called by find_technical_tables
        pass
    
    def split_table_row(self, text):
        """Intelligently split table rows based on patterns"""
        # Common patterns for splitting
        if "F-" in text and any(keyword in text.lower() for keyword in ["must-have", "should-have", "high", "medium", "low"]):
            # Functional requirements table
            parts = re.split(r'\s{3,}', text)  # Split on multiple spaces
            if len(parts) < 3:
                # Try splitting on specific keywords
                parts = re.split(r'(Must-Have|Should-Have|High|Medium|Low)', text)
                parts = [p.strip() for p in parts if p.strip()]
        elif any(dep_type in text for dep_type in ["Prerequisite", "System", "External", "Integration"]):
            # Dependencies table
            for dep_type in ["Prerequisite Features", "System Dependencies", "External Dependencies", "Integration Requirements"]:
                if dep_type in text:
                    parts = [dep_type, text.replace(dep_type, "").strip()]
                    break
            else:
                parts = re.split(r'\s{3,}', text)
        else:
            # General splitting
            parts = re.split(r'\s{3,}', text)
            if len(parts) == 1:
                # Try splitting on common delimiters
                parts = re.split(r'[,;]\s*', text)
        # Clean fragments to fix broken hyphenation or stray soft hyphens
        cleaned_parts = [self._clean_text_fragments(part) for part in parts]
        return [part.strip() for part in cleaned_parts if part and part.strip()]
    
    def is_table_row(self, text):
        """Determine if text looks like a table row"""
        indicators = [
            "F-" in text,  # Requirement IDs
            any(word in text for word in ["Prerequisite", "System", "External", "Integration"]),
            any(word in text for word in ["Must-Have", "Should-Have", "High", "Medium", "Low"]),
            any(word in text.lower() for word in ["user adoption", "economic impact", "cultural preservation"]),
            text.count("\t") > 1,  # Multiple tabs suggest columns
            len(re.findall(r'\s{3,}', text)) > 1  # Multiple large spaces
        ]
        return any(indicators)
    
    def is_section_break(self, text):
        """Determine if text indicates a section break"""
        section_indicators = [
            re.match(r'^\d+\.', text),  # Numbered sections
            any(word in text.lower() for word in ["technical specifications", "functional requirements", "user benefits"]),
            len(text) > 50 and text.isupper(),  # Long uppercase text
            "User Benefits:" in text or "Technical Context:" in text
        ]
        return any(section_indicators)

    # ---- Advanced text reflow and hyphenation repair ----
    def _clean_text_fragments(self, text: str) -> str:
        """Clean text fragments by removing soft hyphens and repairing hyphenation splits within a single string.
        This doesn't join across lines; it only normalizes within the fragment itself.
        """
        if not text:
            return text
        # Remove soft hyphen characters
        text = text.replace('\u00AD', '')
        # Join hyphenated breaks where a hyphen is followed by whitespace and a lowercase continuation
        # Example: "cultural-\n heritage" -> "cultural heritage"
        text = re.sub(r'(\w)-\s+([a-z])', r'\1\2', text)
        # Normalize multiple spaces
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def _should_merge_paragraphs(self, prev_text: str, next_text: str) -> bool:
        """Heuristics to decide if two adjacent paragraph lines should be merged into one continuous paragraph."""
        if not prev_text or not next_text:
            return False
        a = prev_text.rstrip()
        b = next_text.lstrip()

        # Do not merge if the next line appears to be a bullet or enumerated list item
        bullet_like = re.match(r'^(\u2022|\-|\–|\—|\*|\u25AA|\u25E6|\d+[\)\.]|[ivxlcdm]+\.|[A-Z]\))\s+', b, flags=re.IGNORECASE)
        if bullet_like:
            return False

        # Do not merge if previous clearly ends a sentence and next starts a new sentence with uppercase
        if re.search(r'[\.!?]\s*$', a) and re.match(r'^[A-Z]', b):
            return False

        # Merge if previous line ends with hyphen (word wrap)
        if a.endswith('-'):
            return True

        # Merge if previous ends with a comma/semicolon/colon (continuation expected)
        if re.search(r'[,:;]\s*$', a):
            return True

        # Merge if next line starts with lowercase letter (likely mid-sentence continuation)
        if re.match(r'^[a-z]', b):
            return True

        # Merge if previous ends with a single letter token (not 'a' or 'I'), e.g., "c" + "ultural"
        if re.search(r'(?<![A-Za-z])[A-HJ-Za-hj-z]$', a) and re.match(r'^[a-z]{2,}', b):
            return True

        return False

    def _merge_paragraph_pair(self, prev_text: str, next_text: str) -> str:
        """Merge two paragraph strings, repairing hyphenation and single-letter splits."""
        a = prev_text.rstrip()
        b = next_text.lstrip()

        # If a ends with hyphen, drop the hyphen and join directly (no space)
        if a.endswith('-'):
            a = a[:-1]
            merged = a + b
        # If a ends with a single letter (excluding 'a'/'I') and b starts with lowercase, join without space
        elif re.search(r'(?<![A-Za-z])[A-HJ-Za-hj-z]$', a) and re.match(r'^[a-z]{2,}', b):
            merged = a + b
        else:
            merged = a + ' ' + b

        # Final cleanup for soft hyphens and accidental hyphenation patterns
        merged = self._clean_text_fragments(merged)
        return merged

    def reflow_content(self, content_structure):
        """Merge broken lines and words to produce well-formed paragraphs.
        Operates on the linear content structure, only merging adjacent 'paragraph' items on the same page.
        """
        if not content_structure:
            return content_structure

        reflowed = []
        for item in content_structure:
            # Clean each item's text fragments
            item_text = self._clean_text_fragments(item.get('text', ''))
            item['text'] = item_text

            if reflowed and item['type'] == 'paragraph' and reflowed[-1]['type'] == 'paragraph' and item['page'] == reflowed[-1]['page']:
                prev = reflowed[-1]
                if self._should_merge_paragraphs(prev['text'], item['text']):
                    prev['text'] = self._merge_paragraph_pair(prev['text'], item['text'])
                    # Keep the earlier item's font size/bold; skip appending the current
                    continue

            reflowed.append(item)

        return reflowed
    
    def process_text_with_hierarchy(self):
        """Process text content preserving the hierarchical structure"""
        print("Processing text with hierarchical structure...")
        
        content_structure = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            # Extract lines with positions
            page_lines = self._extract_page_lines_with_positions(page, page_num)
            # Reorder by columns if a multi-column layout is detected
            ordered_lines = self._reorder_lines_by_columns(page_lines)
            content_structure.extend(ordered_lines)
        
        return content_structure

    def _extract_page_lines_with_positions(self, page, page_num):
        """Extract lines with text, styles, and approximate top-left position for each line."""
        text_dict = page.get_text("dict")
        lines_out = []
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = ""
                max_font_size = 0
                is_bold = False
                x0 = None
                y0 = None
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    if not span_text:
                        continue
                    line_text += span_text
                    max_font_size = max(max_font_size, span.get("size", 0))
                    if span.get("flags", 0) & 2**4:
                        is_bold = True
                    if x0 is None or y0 is None:
                        bbox = span.get("bbox")
                        if bbox and len(bbox) >= 2:
                            try:
                                x0 = float(bbox[0])
                                y0 = float(bbox[1])
                            except Exception:
                                x0, y0 = 0.0, 0.0
                line_text = line_text.strip()
                if not line_text:
                    continue
                text_type = self.classify_text_type(line_text, max_font_size, is_bold)
                lines_out.append({
                    'text': line_text,
                    'page': page_num,
                    'type': text_type,
                    'font_size': max_font_size,
                    'is_bold': is_bold,
                    'x0': x0 if x0 is not None else 0.0,
                    'y0': y0 if y0 is not None else 0.0,
                })
        return lines_out

    def _reorder_lines_by_columns(self, lines):
        """Reorder lines to respect multi-column layouts using x-positions."""
        if not lines:
            return lines
        # Sort by y, then x as a baseline
        baseline = sorted(lines, key=lambda it: (it.get('y0', 0.0), it.get('x0', 0.0)))
        # Collect x-positions of paragraph-like items
        para_x = [round(it.get('x0', 0.0), 1) for it in baseline if it['type'] in ('paragraph', 'bold_header')]
        if len(para_x) < 8:
            return baseline
        para_x_sorted = sorted(set(para_x))
        # Find largest gap in x to split columns
        gaps = []
        for i in range(1, len(para_x_sorted)):
            gaps.append((para_x_sorted[i] - para_x_sorted[i - 1], i))
        if not gaps:
            return baseline
        largest_gap, idx = max(gaps, key=lambda g: g[0])
        if largest_gap < 40:  # No strong indication of separate columns
            return baseline
        threshold = (para_x_sorted[idx - 1] + para_x_sorted[idx]) / 2.0
        for it in baseline:
            it['__col'] = 0 if it.get('x0', 0.0) < threshold else 1
        # Read col 0 top→bottom, then col 1 top→bottom
        return sorted(baseline, key=lambda it: (it['__col'], it.get('y0', 0.0), it.get('x0', 0.0)))
    
    def classify_text_type(self, text, font_size, is_bold):
        """Classify text based on patterns from the document"""
        # Main section headers (like "Technical Specifications")
        if font_size >= 16 or (is_bold and any(word in text for word in ["Technical Specifications", "INTRODUCTION", "SYSTEM OVERVIEW", "PROCESS FLOWCHART"])):
            return "main_title"
        
        # Numbered sections (1. INTRODUCTION, 1.2 SYSTEM OVERVIEW, etc.)
        if re.match(r'^\d+\.?\d*\s+[A-Z\s]+$', text) or re.match(r'^\d+\.\d+\s+[A-Za-z\s]+$', text):
            return "section_header"
        
        # Subsection headers (1.1 Brief Overview, etc.)
        if re.match(r'^\d+\.\d+\.\d+\s+[A-Za-z\s]+$', text):
            return "subsection_header"
        
        # Bold headers that aren't numbered
        if is_bold and len(text) < 100 and not text.endswith('.'):
            return "bold_header"
        
        # Regular paragraph text
        return "paragraph"
    
    def build_structured_content(self, content_structure):
        """Build structured HTML content from the processed text"""
        html_content = ""
        current_section = None
        section_content = ""
        section_id = 0
        
        toc_items = []
        # List reconstruction state
        list_stack = []  # stack of {'type': 'ul'|'ol', 'level': int}
        # Current section anchor for tables
        section_anchor = {'page': None, 'y0': None}
        
        for item in content_structure:
            text = item['text']
            text_type = item['type']
            x0 = item.get('x0', 0.0)
            
            if text_type == "main_title":
                # Save previous section
                if current_section and section_content:
                    # Close any open lists first
                    while list_stack:
                        section_content += f"</{list_stack.pop()['type']}>\n"
                    # Append section content and then insert nearby tables in reading order
                    section_html = self.wrap_section(current_section, section_content, section_id)
                    section_html = section_html.replace('</div>\n        </section>', f"{self.insert_relevant_tables(section_id, section_anchor['y0'], section_anchor['page'])}</div>\n        </section>")
                    html_content += section_html
                    section_content = ""
                
                section_id += 1
                current_section = text
                toc_items.append({
                    'title': text,
                    'id': f"section-{section_id}",
                    'level': 1
                })
                # Reset section anchor on new main title
                section_anchor = {'page': None, 'y0': None}
                
            elif text_type == "section_header":
                while list_stack:
                    section_content += f"</{list_stack.pop()['type']}>\n"
                html_content += f'<h2 class="section-header">{text}</h2>\n'
                # Reset anchor on heading boundary
                section_anchor = {'page': item.get('page'), 'y0': item.get('y0')}
                
            elif text_type == "subsection_header":
                while list_stack:
                    section_content += f"</{list_stack.pop()['type']}>\n"
                html_content += f'<h3 class="subsection-header">{text}</h3>\n'
                section_anchor = {'page': item.get('page'), 'y0': item.get('y0')}
                
            elif text_type == "bold_header":
                while list_stack:
                    section_content += f"</{list_stack.pop()['type']}>\n"
                html_content += f'<h4 class="bold-header">{text}</h4>\n'
                section_anchor = {'page': item.get('page'), 'y0': item.get('y0')}
                
            elif text_type == "paragraph":
                # Skip very short lines that might be artifacts
                if len(text.strip()) > 1:
                    # Detect and reconstruct lists
                    list_info = self._parse_list_item(text, x0)
                    if list_info:
                        level = list_info['level']
                        list_type = list_info['type']
                        # Close deeper lists
                        while list_stack and list_stack[-1]['level'] > level:
                            section_content += f"</{list_stack.pop()['type']}>\n"
                        # Switch list type at same level
                        if list_stack and list_stack[-1]['level'] == level and list_stack[-1]['type'] != list_type:
                            section_content += f"</{list_stack.pop()['type']}>\n"
                        # Open lists up to the desired level
                        while not list_stack or list_stack[-1]['level'] < level or (list_stack[-1]['level'] == level and list_stack[-1]['type'] != list_type):
                            section_content += f"<{list_type}>\n"
                            new_level = (list_stack[-1]['level'] + 1) if list_stack else 0
                            list_stack.append({'type': list_type, 'level': new_level})
                            if new_level >= level:
                                break
                        section_content += f"<li>{list_info['content']}</li>\n"
                    else:
                        # Close any open lists before a normal paragraph
                        while list_stack:
                            section_content += f"</{list_stack.pop()['type']}>\n"
                        section_content += f'<p class="content-paragraph">{text}</p>\n'
                        # First paragraph after a header becomes the section anchor for table placement
                        if section_anchor['page'] is None:
                            section_anchor = {'page': item.get('page'), 'y0': item.get('y0')}
        
        # Add final section
        if current_section and section_content:
            while list_stack:
                section_content += f"</{list_stack.pop()['type']}>\n"
            section_html = self.wrap_section(current_section, section_content, section_id)
            section_html = section_html.replace('</div>\n        </section>', f"{self.insert_relevant_tables(section_id, section_anchor['y0'], section_anchor['page'])}</div>\n        </section>")
            html_content += section_html
        
        return html_content, toc_items

    def _parse_list_item(self, text: str, x0: float):
        """Parse list-like markers and return normalized structure or None.
        Returns {'type': 'ul'|'ol', 'content': str, 'level': int}
        """
        stripped = text.strip()
        # Bullets
        m = re.match(r'^(\u2022|\-|\–|\—|\*|\u25AA|\u25E6)\s+(.*)$', stripped)
        if m:
            return {'type': 'ul', 'content': m.group(2).strip(), 'level': self._indent_level_from_x(x0)}
        # Numbered
        m = re.match(r'^((\d+|[A-Za-z]|[ivxlcdm]+)[\)\.])\s+(.*)$', stripped, flags=re.IGNORECASE)
        if m:
            return {'type': 'ol', 'content': m.group(3).strip(), 'level': self._indent_level_from_x(x0)}
        return None

    def _indent_level_from_x(self, x0: float) -> int:
        """Map x-offset to a list nesting level using a coarse 24px step beyond a base margin."""
        if x0 is None:
            return 0
        base = 36.0
        if x0 <= base:
            return 0
        return int((x0 - base) // 24.0)
    
    def wrap_section(self, title, content, section_id):
        """Wrap content in a section with proper styling"""
        section_html = f'''
        <section id="section-{section_id}" class="document-section">
            <div class="section-header-wrapper">
                <h1 class="section-title">{title}</h1>
            </div>
            <div class="section-content">
                {content}
                {self.insert_relevant_images(section_id)}
            </div>
        </section>
        '''
        return section_html
    
    def insert_relevant_tables(self, section_id, section_y0=None, section_page=None):
        """Insert tables relevant to the current section in reading order.
        If a table has page/y0 metadata, keep the order by (same page first, then closest y0 after the section header).
        """
        table_html = ""
        
        # Map sections to table types
        section_table_map = {
            1: ['stakeholder', 'grid'],
            2: ['technical', 'grid'],
            3: ['technical', 'grid'],
            4: ['technical', 'grid']
        }
        
        relevant_types = section_table_map.get(section_id, [])
        
        # Filter then sort by proximity if we have positional hints
        candidate_tables = [t for t in self.tables if t.get('type') in relevant_types]

        def table_sort_key(t):
            page = t.get('page', 0)
            y0 = t.get('y0', None)
            if section_page is None or section_y0 is None or y0 is None:
                return (page, y0 if y0 is not None else 1e9)
            # Prefer same page and y0 after section start
            penalty = 0 if page == section_page else abs(page - section_page) * 10000
            delta = (y0 - section_y0) if page == section_page else 1e6
            return (penalty, delta)

        candidate_tables.sort(key=table_sort_key)

        for table in candidate_tables:
                table_html += self.generate_professional_table(table)
        
        return table_html
    
    def insert_relevant_images(self, section_id):
        """Insert images/diagrams relevant to the current section"""
        image_html = ""
        
        for image in self.images:
            # Skip likely watermark images
            if image.get('is_watermark'):
                continue
            # Simple heuristic: distribute images based on page and section
            if section_id == 3 and image.get('is_diagram'):  # System diagrams in section 3
                image_html += self.generate_diagram_html(image)
            elif section_id == 5 and image.get('is_diagram'):  # Flowcharts in section 5
                image_html += self.generate_flowchart_html(image)
        
        return image_html
    
    def generate_professional_table(self, table):
        """Generate professional table HTML matching the document style"""
        if not table['data'] or len(table['data']) < 2:
            return ""
        
        table_html = f'''
        <div class="professional-table-container">
            <h4 class="table-title">{table.get('title', 'Table')}</h4>
            <div class="table-wrapper">
                <table class="professional-table">
                    <thead>
                        <tr>
        '''
        
        # Add headers
        headers = table['data'][0]
        for header in headers:
            table_html += f'<th class="table-header">{header}</th>'
        
        table_html += '</tr></thead><tbody>'
        
        # Add data rows
        for row in table['data'][1:]:
            table_html += '<tr class="table-row">'
            for i, cell in enumerate(row):
                cell_class = "table-cell"
                if i == 0:  # First column
                    cell_class += " first-column"
                table_html += f'<td class="{cell_class}">{cell}</td>'
            
            # Pad row if needed
            while len(row) < len(headers):
                row.append("")
                table_html += '<td class="table-cell"></td>'
            
            table_html += '</tr>'
        
        table_html += '''
                </tbody>
            </table>
        </div>
    </div>
        '''
        
        return table_html
    
    def generate_diagram_html(self, image):
        """Generate HTML for system diagrams"""
        return f'''
        <div class="diagram-container">
            <h4 class="diagram-title">System Architecture Diagram</h4>
            <div class="diagram-wrapper">
                <img src="{image['data']}" alt="System Diagram" class="system-diagram" />
            </div>
            <p class="diagram-caption">Figure: System components and their relationships</p>
        </div>
        '''
    
    def generate_flowchart_html(self, image):
        """Generate HTML for flowcharts"""
        return f'''
        <div class="flowchart-container">
            <h4 class="flowchart-title">Process Flowchart</h4>
            <div class="flowchart-wrapper">
                <img src="{image['data']}" alt="Process Flowchart" class="process-flowchart" />
            </div>
            <p class="flowchart-caption">Figure: System workflow and decision points</p>
        </div>
        '''
    
    def get_document_styles(self):
        """Get CSS styles that match the document design exactly"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #ffffff;
            font-size: 14px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: white;
        }
        
        /* Header Styles */
        .document-header {
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 20px;
            margin-bottom: 40px;
        }
        
        .main-title {
            font-size: 24px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }
        
        /* Section Styles */
        .document-section {
            margin-bottom: 50px;
            page-break-inside: avoid;
        }
        
        .section-header-wrapper {
            margin-bottom: 30px;
        }
        
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .section-header {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin: 30px 0 15px 0;
            padding-bottom: 5px;
        }
        
        .subsection-header {
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin: 25px 0 12px 0;
        }
        
        .bold-header {
            font-size: 14px;
            font-weight: 600;
            color: #34495e;
            margin: 20px 0 10px 0;
        }
        
        /* Text Content */
        .section-content {
            line-height: 1.7;
        }
        
        .content-paragraph {
            margin-bottom: 15px;
            text-align: justify;
            color: #2c3e50;
            font-size: 14px;
            line-height: 1.7;
        }
        
        /* Professional Table Styles */
        .professional-table-container {
            margin: 30px 0;
            width: 100%;
        }
        
        .table-title {
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
        }
        
        .table-wrapper {
            width: 100%;
            overflow-x: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }
        
        .professional-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            background: white;
        }
        
        .table-header {
            background: #f8f9fa;
            color: #2c3e50;
            font-weight: 600;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 2px solid #e0e0e0;
            border-right: 1px solid #e0e0e0;
            white-space: nowrap;
        }
        
        .table-header:last-child {
            border-right: none;
        }
        
        .table-row {
            border-bottom: 1px solid #e0e0e0;
        }
        
        .table-row:nth-child(even) {
            background: #fafafa;
        }
        
        .table-row:hover {
            background: #f0f8ff;
        }
        
        .table-cell {
            padding: 12px 15px;
            border-right: 1px solid #e0e0e0;
            vertical-align: top;
            line-height: 1.5;
        }
        
        .table-cell:last-child {
            border-right: none;
        }
        
        .first-column {
            font-weight: 500;
            background: #f8f9fa;
            color: #2c3e50;
        }
        
        /* Diagram Styles */
        .diagram-container, .flowchart-container {
            margin: 40px 0;
            text-align: center;
            background: #fafafa;
            padding: 30px 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        
        .diagram-title, .flowchart-title {
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        .diagram-wrapper, .flowchart-wrapper {
            margin: 20px 0;
        }
        
        .system-diagram, .process-flowchart {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .diagram-caption, .flowchart-caption {
            font-size: 12px;
            color: #7f8c8d;
            font-style: italic;
            margin-top: 15px;
        }
        
        /* Navigation Styles */
        .nav-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 280px;
            height: 100vh;
            background: #2c3e50;
            color: white;
            padding: 20px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }
        
        .nav-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
            border-bottom: 1px solid #34495e;
            padding-bottom: 15px;
        }
        
        .nav-list {
            list-style: none;
            padding: 0;
        }
        
        .nav-item {
            margin-bottom: 10px;
        }
        
        .nav-link {
            color: #ecf0f1;
            text-decoration: none;
            display: block;
            padding: 10px 15px;
            border-radius: 4px;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        .nav-link:hover, .nav-link.active {
            background: #3498db;
            text-decoration: none;
            transform: translateX(5px);
        }
        
        .main-content {
            margin-left: 300px;
            padding: 20px 40px;
        }
        
        /* Responsive Design */
        @media (max-width: 1024px) {
            .nav-container {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }
            
            .nav-container.open {
                transform: translateX(0);
            }
            
            .main-content {
                margin-left: 0;
                padding: 20px;
            }
            
            .container {
                padding: 20px 10px;
            }
        }
        
        @media (max-width: 768px) {
            .main-title {
                font-size: 20px;
            }
            
            .section-title {
                font-size: 18px;
            }
            
            .professional-table {
                font-size: 12px;
            }
            
            .table-header, .table-cell {
                padding: 8px 10px;
            }
            
            .diagram-container, .flowchart-container {
                padding: 20px 15px;
            }
        }
        
        /* Print Styles */
        @media print {
            .nav-container {
                display: none;
            }
            
            .main-content {
                margin-left: 0;
            }
            
            .document-section {
                break-inside: avoid;
            }
            
            .professional-table-container {
                break-inside: avoid;
            }
        }
        
        /* Utility Classes */
        .text-center { text-align: center; }
        .text-bold { font-weight: 600; }
        .mb-10 { margin-bottom: 10px; }
        .mb-20 { margin-bottom: 20px; }
        .mb-30 { margin-bottom: 30px; }
        """
    
    def generate_html(self):
        """Generate the final HTML file matching the document style"""
        print("Generating professional HTML document...")
        
        # Process all content
        self.extract_images()
        self.detect_tables_advanced()
        content_structure = self.process_text_with_hierarchy()
        # Reflow text to fix broken words and incorrect line breaks
        content_structure = self.reflow_content(content_structure)
        html_content, toc_items = self.build_structured_content(content_structure)
        
        # Generate navigation
        nav_html = '<ul class="nav-list">'
        for item in toc_items:
            nav_html += f'''
            <li class="nav-item">
                <a href="#{item['id']}" class="nav-link">{item['title']}</a>
            </li>'''
        nav_html += '</ul>'
        
        # Get document title
        doc_title = self.doc.metadata.get('title', Path(self.pdf_path).stem.replace('_', ' ').title())
        
        # Generate complete HTML
        html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc_title}</title>
    <style>{self.get_document_styles()}</style>
</head>
<body>
    <nav class="nav-container">
        <h1 class="nav-title">Table of Contents</h1>
        {nav_html}
    </nav>
    
    <main class="main-content">
        <div class="container">
            <header class="document-header">
                <h1 class="main-title">{doc_title}</h1>
            </header>
            
            {html_content}
        </div>
    </main>
    
    <script>
        // Smooth scrolling navigation
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'start'
                    }});
                }}
            }});
        }});
        
        // Mobile navigation toggle
        function toggleNav() {{
            const nav = document.querySelector('.nav-container');
            nav.classList.toggle('open');
        }}

        </script>
</body>
</html>
        '''

        # Save HTML output
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_template)

        print(f"HTML document generated successfully: {self.output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDF to structured HTML")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("output_file", help="Path to the output HTML file")

    args = parser.parse_args()

    converter = PDFToHTMLConverter(args.pdf_path, args.output_file)
    converter.generate_html()