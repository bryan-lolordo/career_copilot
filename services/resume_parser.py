# services/resume_parser.py
import os
import io
import pdfplumber
from docx import Document
import mammoth
from html.parser import HTMLParser


def parse_resume(file) -> str:
    """
    Extract plain text from a résumé file (PDF or DOCX) with bullet preservation.
    
    Args:
        file: Either a file path (str) OR a Streamlit UploadedFile object
    
    Returns:
        Extracted text with preserved line structure and bullets
    """
    # Handle Streamlit UploadedFile
    if hasattr(file, 'read'):
        file_bytes = file.read()
        file_name = file.name
        ext = os.path.splitext(file_name)[1].lower()
        
        text = ""
        
        if ext == ".pdf":
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                raise ValueError(f"Error parsing PDF: {str(e)}")
        
        elif ext == ".docx":
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                
                # Use python-docx to detect bullets
                text = _parse_docx_with_bullets(tmp_path)
                os.unlink(tmp_path)
            except Exception as e:
                raise ValueError(f"Error parsing DOCX: {str(e)}")
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    # Handle file path string
    else:
        file_path = file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        
        if ext == ".pdf":
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                raise ValueError(f"Error parsing PDF: {str(e)}")
        
        elif ext == ".docx":
            try:
                text = _parse_docx_with_bullets(file_path)
            except Exception as e:
                raise ValueError(f"Error parsing DOCX: {str(e)}")
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    # Clean excessive whitespace while preserving structure
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        cleaned_line = ' '.join(line.split())
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    
    clean_text = '\n'.join(cleaned_lines)
    
    if not clean_text or len(clean_text) < 50:
        raise ValueError("Could not extract meaningful text from the file.")
    
    return clean_text


def _parse_docx_with_bullets(file_path: str) -> str:
    """Parse DOCX using mammoth for better formatting preservation."""
    import mammoth
    from html.parser import HTMLParser
    
    # Convert DOCX to HTML
    with open(file_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
    
    # Parse HTML to clean text with bullets preserved
    class ResumeHTMLParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.lines = []
            self.current_line = []
            self.in_list = False
            
        def handle_starttag(self, tag, attrs):
            if tag == 'li':
                self.in_list = True
            elif tag in ['p', 'h1', 'h2', 'h3', 'h4']:
                # New paragraph
                if self.current_line:
                    line = ' '.join(self.current_line).strip()
                    if line:
                        self.lines.append(line)
                    self.current_line = []
        
        def handle_endtag(self, tag):
            if tag == 'li':
                line = ' '.join(self.current_line).strip()
                if line:
                    self.lines.append(f"• {line}")
                self.current_line = []
                self.in_list = False
            elif tag in ['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol']:
                if self.current_line:
                    line = ' '.join(self.current_line).strip()
                    if line:
                        if self.in_list:
                            self.lines.append(f"• {line}")
                        else:
                            self.lines.append(line)
                    self.current_line = []
        
        def handle_data(self, data):
            data = data.strip()
            if data:
                self.current_line.append(data)
        
        def get_text(self):
            # Flush any remaining content
            if self.current_line:
                line = ' '.join(self.current_line).strip()
                if line:
                    self.lines.append(line)
            
            # POST-PROCESSING: Merge broken paragraph lines
            merged = []
            i = 0
            while i < len(self.lines):
                line = self.lines[i]
                
                # If it's a header (all caps, short)
                if line.isupper() and len(line.split()) <= 5:
                    if merged:
                        merged.append("")  # Add spacing before header
                    merged.append(line)
                    merged.append("")  # Add spacing after header
                    i += 1
                # If it's a bullet point
                elif line.startswith('•'):
                    merged.append(line)
                    i += 1
                # If it's a regular line that doesn't end with punctuation
                # AND next line doesn't start with bullet/caps = continuation
                elif i + 1 < len(self.lines) and \
                     not line.endswith(('.', '!', '?')) and \
                     not self.lines[i + 1].startswith('•') and \
                     not (self.lines[i + 1].isupper() and len(self.lines[i + 1].split()) <= 5):
                    # Merge with next line
                    merged.append(line + " " + self.lines[i + 1])
                    i += 2
                else:
                    merged.append(line)
                    i += 1
            
            return '\n'.join(merged)
    
    parser = ResumeHTMLParser()
    parser.feed(html)
    
    return parser.get_text()

def get_supported_extensions():
    """Returns a list of supported file extensions."""
    return ['.pdf', '.docx']


def is_supported_file(file_path: str) -> bool:
    """Check if a file is a supported resume format."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in get_supported_extensions()