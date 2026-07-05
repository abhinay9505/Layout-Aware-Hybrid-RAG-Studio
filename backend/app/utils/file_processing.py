import re
import unicodedata
from fastapi import HTTPException
from langchain_core.documents import Document as LangDocument

class FileValidator:
    ALLOWED_EXTENSIONS = [
        # Documents
        ".pdf", ".docx",
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
        # Audio
        ".mp3", ".wav", ".m4a", ".ogg", ".flac",
        # Video
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
    ]

    # Max file sizes in bytes
    MAX_SIZES = {
        "document": 50 * 1024 * 1024,   # 50 MB
        "image": 20 * 1024 * 1024,       # 20 MB
        "audio": 100 * 1024 * 1024,      # 100 MB
        "video": 200 * 1024 * 1024,      # 200 MB
    }

    @classmethod
    def get_file_type(cls, filename):
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in {".pdf", ".docx"}:
            return "document"
        elif ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            return "image"
        elif ext in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
            return "audio"
        elif ext in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
            return "video"
        return None

    @classmethod
    async def validate(cls, file):
        valid = any([file.filename.endswith(ext) for ext in cls.ALLOWED_EXTENSIONS])
        if not valid:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )

class TextCleaner:
    @staticmethod
    def clean(text):
        # Remove non-printable control characters, preserving spaces, newlines, and markdown syntax
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        return text.strip()

class TextNormalizer:
    @staticmethod
    def normalize(text):
        # Don't lowercase for media — preserve proper nouns from transcriptions
        text = unicodedata.normalize('NFKD', text)
        return text.encode('ascii', 'ignore').decode('utf-8')

class MarkdownElementParser:
    @staticmethod
    def parse(markdown_text, page_num):
        lines = markdown_text.split("\n")
        elements = []
        current_section = "Header/Title"
        
        in_table = False
        table_lines = []
        
        in_blockquote = False
        blockquote_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 1. Heading detection (e.g. # Section 3.1, or "3.1 Pre-training BERT")
            if stripped.startswith("#"):
                # Flush pending elements
                if in_table and table_lines:
                    elements.append({
                        "type": "table",
                        "content": "\n".join(table_lines),
                        "section": current_section,
                        "page_num": page_num
                    })
                    table_lines = []
                    in_table = False
                if in_blockquote and blockquote_lines:
                    content = "\n".join(blockquote_lines)
                    content_type = "figure" if any(x in content.lower() for x in ["figure", "fig.", "table"]) else "blockquote"
                    elements.append({
                        "type": content_type,
                        "content": content,
                        "section": current_section,
                        "page_num": page_num
                    })
                    blockquote_lines = []
                    in_blockquote = False
                
                heading_text = stripped.lstrip("#").strip()
                current_section = heading_text
                elements.append({
                    "type": "heading",
                    "content": stripped,
                    "section": current_section,
                    "page_num": page_num
                })
                i += 1
                continue
                
            # 2. Table detection
            if stripped.startswith("|"):
                if in_blockquote and blockquote_lines:
                    content = "\n".join(blockquote_lines)
                    content_type = "figure" if any(x in content.lower() for x in ["figure", "fig.", "table"]) else "blockquote"
                    elements.append({
                        "type": content_type,
                        "content": content,
                        "section": current_section,
                        "page_num": page_num
                    })
                    blockquote_lines = []
                    in_blockquote = False
                in_table = True
                table_lines.append(line)
                i += 1
                continue
            elif in_table:
                if not stripped.startswith("|") and stripped != "":
                    # Table finished
                    elements.append({
                        "type": "table",
                        "content": "\n".join(table_lines),
                        "section": current_section,
                        "page_num": page_num
                    })
                    table_lines = []
                    in_table = False
                else:
                    table_lines.append(line)
                    i += 1
                    continue
                    
            # 3. Blockquote / Figure detection (vision parser blockquotes)
            if stripped.startswith(">"):
                if in_table and table_lines:
                    elements.append({
                        "type": "table",
                        "content": "\n".join(table_lines),
                        "section": current_section,
                        "page_num": page_num
                    })
                    table_lines = []
                    in_table = False
                in_blockquote = True
                blockquote_lines.append(line.lstrip(">").strip())
                i += 1
                continue
            elif in_blockquote:
                if not stripped.startswith(">") and stripped != "":
                    # Blockquote finished
                    content = "\n".join(blockquote_lines)
                    content_type = "figure" if any(x in content.lower() for x in ["figure", "fig.", "table"]) else "blockquote"
                    elements.append({
                        "type": content_type,
                        "content": content,
                        "section": current_section,
                        "page_num": page_num
                    })
                    blockquote_lines = []
                    in_blockquote = False
                else:
                    blockquote_lines.append(line.lstrip(">").strip())
                    i += 1
                    continue
                    
            # 4. Paragraph
            if stripped:
                if re.match(r"^(?:Figure|Fig\.)\s+\d+", stripped, re.IGNORECASE):
                    elements.append({
                        "type": "figure",
                        "content": stripped,
                        "section": current_section,
                        "page_num": page_num
                    })
                else:
                    elements.append({
                        "type": "paragraph",
                        "content": stripped,
                        "section": current_section,
                        "page_num": page_num
                    })
            i += 1
            
        # Flush remaining
        if in_table and table_lines:
            elements.append({
                "type": "table",
                "content": "\n".join(table_lines),
                "section": current_section,
                "page_num": page_num
            })
        if in_blockquote and blockquote_lines:
            content = "\n".join(blockquote_lines)
            content_type = "figure" if any(x in content.lower() for x in ["figure", "fig.", "table"]) else "blockquote"
            elements.append({
                "type": content_type,
                "content": content,
                "section": current_section,
                "page_num": page_num
            })
            
        return elements

def convert_table_to_structured_text(markdown_table):
    lines = [l.strip() for l in markdown_table.strip().split("\n") if l.strip()]
    if len(lines) < 3:
        return markdown_table
        
    def parse_row(row_str):
        parts = [p.strip() for p in row_str.split("|")]
        if parts and parts[0] == "":
            parts.pop(0)
        if parts and parts[-1] == "":
            parts.pop()
        return parts
        
    headers = parse_row(lines[0])
    rows = []
    for line in lines[2:]:
        row_data = parse_row(line)
        if len(row_data) == len(headers):
            rows.append(row_data)
            
    structured_parts = []
    for r_idx, row in enumerate(rows):
        row_str = ", ".join(f"{headers[c_idx]}: {val}" for c_idx, val in enumerate(row) if c_idx < len(headers))
        structured_parts.append(row_str)
        
    return "\n".join(structured_parts)

def convert_markdown_table_to_json(markdown_table, page_num, section_name):
    import json
    table_json = {
        "type": "table",
        "page": page_num,
        "content": markdown_table.strip()
    }
    return json.dumps(table_json, indent=1)

class SemanticChunker:
    def __init__(self, chunk_size=4000, chunk_overlap=600):
        # 4000 chars is roughly 1000 tokens
        # 600 chars is roughly 150 tokens
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_paragraphs_to_sentences(self, paragraphs_text):
        # Split text into sentences using simple sentence-splitting regex
        sentences = re.split(r'(?<=[.!?])\s+', paragraphs_text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_elements(self, elements):
        chunks = []
        
        # Group text elements by section
        sections = {}
        for elem in elements:
            sec = elem["section"]
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(elem)
            
        for sec_name, sec_elements in sections.items():
            text_paragraphs = []
            
            for elem in sec_elements:
                if elem["type"] == "table":
                    table_md = elem["content"]
                    table_json_str = convert_markdown_table_to_json(table_md, elem["page_num"], sec_name)
                    
                    chunks.append(LangDocument(
                        page_content=table_json_str,
                        metadata={
                            "section_name": sec_name,
                            "page_num": elem["page_num"],
                            "content_type": "table"
                        }
                    ))
                elif elem["type"] == "figure":
                    caption_desc = elem["content"]
                    combined_figure_content = f"Figure from section '{sec_name}':\n\n{caption_desc}"
                    
                    chunks.append(LangDocument(
                        page_content=combined_figure_content,
                        metadata={
                            "section_name": sec_name,
                            "page_num": elem["page_num"],
                            "content_type": "figure"
                        }
                    ))
                elif elem["type"] in ["paragraph", "heading", "blockquote"]:
                    text_paragraphs.append(elem)
            
            # Now semantic chunk text paragraphs
            if text_paragraphs:
                merged_text = "\n\n".join([p["content"] for p in text_paragraphs])
                sentences = self.split_paragraphs_to_sentences(merged_text)
                
                current_chunk_sentences = []
                current_len = 0
                
                for sentence in sentences:
                    s_len = len(sentence)
                    if current_len + s_len > self.chunk_size and current_chunk_sentences:
                        chunk_text = " ".join(current_chunk_sentences)
                        full_content = f"Section: {sec_name}\n\n{chunk_text}"
                        page_num = text_paragraphs[0]["page_num"]
                        
                        chunks.append(LangDocument(
                            page_content=full_content,
                            metadata={
                                "section_name": sec_name,
                                "page_num": page_num,
                                "content_type": "text"
                            }
                        ))
                        
                        # Apply overlap
                        overlap_sentences = []
                        overlap_len = 0
                        for s in reversed(current_chunk_sentences):
                            if overlap_len + len(s) < self.chunk_overlap:
                                overlap_sentences.insert(0, s)
                                overlap_len += len(s) + 1
                            else:
                                break
                        current_chunk_sentences = overlap_sentences
                        current_len = overlap_len
                        
                    current_chunk_sentences.append(sentence)
                    current_len += s_len + 1
                    
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    full_content = f"Section: {sec_name}\n\n{chunk_text}"
                    page_num = text_paragraphs[0]["page_num"]
                    
                    chunks.append(LangDocument(
                        page_content=full_content,
                        metadata={
                            "section_name": sec_name,
                            "page_num": page_num,
                            "content_type": "text"
                        }
                    ))
                    
        return chunks

# Keep compatibility with existing codebase
class RecursiveChunker:
    def __init__(self, chunk_size=1500, chunk_overlap=300):
        self.chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split(self, text, page_num=1):
        elements = MarkdownElementParser.parse(text, page_num)
        return self.chunker.chunk_elements(elements)

