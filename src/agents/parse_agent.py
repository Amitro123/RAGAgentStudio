"""
Parse Agent - handles file conversion and text extraction
Converts various file formats to PDF
"""
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from .agent_base import BaseAgent
import logging

logger = logging.getLogger(__name__)


class ParseAgent(BaseAgent):
    """
    File parsing and conversion agent
    
    Supports:
    - DOCX -> PDF
    - TXT -> PDF
    - JSON -> PDF
    - Extracts text from PDFs
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "parse_agent"
        self.temp_dir = tempfile.gettempdir()
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate parsing input
        
        Expected input:
        {
            "file": File path or object,
            "file_type": str (docx, txt, json),
            "output_format": str (default: pdf)
        }
        """
        required_fields = ["file", "file_type"]
        
        for field in required_fields:
            if field not in input_data:
                self.log("WARNING", f"Missing required field: {field}")
                return False
        
        return True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and convert file
        
        Returns:
        {
            "status": "success" | "error",
            "file_path": str,
            "file_type": str,
            "output_format": str,
            "file_size": int,
            "text_preview": str
        }
        """
        try:
            self.log("INFO", "Starting file parsing process")
            
            file_obj = input_data.get("file")
            file_type = input_data.get("file_type", "unknown").lower()
            output_format = input_data.get("output_format", "pdf")
            
            self.log("INFO", f"Converting {file_type} to {output_format}")
            
            # Determine conversion method
            if file_type == "pdf":
                # Already PDF, just extract text
                text_preview = await self._extract_pdf_text(file_obj)
                return {
                    "status": "success",
                    "agent_id": self.agent_id,
                    "data": {
                        "file_path": str(file_obj),
                        "file_type": "pdf",
                        "output_format": "pdf",
                        "conversion_needed": False,
                        "text_preview": text_preview[:200]
                    },
                    "message": "PDF file ready for processing"
                }
            
            elif file_type == "docx":
                output_path = await self._convert_docx_to_pdf(file_obj)
                text_preview = await self._extract_pdf_text(output_path)
                
            elif file_type == "txt":
                output_path = await self._convert_txt_to_pdf(file_obj)
                text_preview = await self._extract_pdf_text(output_path)
                
            elif file_type == "json":
                output_path = await self._convert_json_to_pdf(file_obj)
                text_preview = await self._extract_pdf_text(output_path)
                
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            file_size = os.path.getsize(output_path)
            
            self.log("INFO", f"File converted successfully: {output_path}")
            
            return {
                "status": "success",
                "agent_id": self.agent_id,
                "data": {
                    "file_path": output_path,
                    "file_type": file_type,
                    "output_format": "pdf",
                    "conversion_needed": True,
                    "file_size": file_size,
                    "text_preview": text_preview[:200]
                },
                "message": f"File converted to PDF successfully"
            }
        
        except Exception as e:
            self.error(f"File parsing failed: {str(e)}", e)
            return {
                "status": "error",
                "agent_id": self.agent_id,
                "message": str(e),
                "data": None
            }
    
    async def _convert_docx_to_pdf(self, file_path: str) -> str:
        """Convert DOCX to PDF using reportlab"""
        try:
            from docx import Document
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            
            self.log("INFO", "Converting DOCX to PDF")
            
            doc = Document(file_path)
            
            output_path = os.path.join(self.temp_dir, "converted_document.pdf")
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            y = height - 40
            for para in doc.paragraphs:
                if para.text.strip():
                    c.drawString(40, y, para.text[:100])
                    y -= 20
                    if y < 40:
                        c.showPage()
                        y = height - 40
            
            c.save()
            self.log("INFO", f"DOCX converted to {output_path}")
            
            return output_path
        
        except Exception as e:
            self.error(f"DOCX conversion failed: {str(e)}", e)
            raise
    
    async def _convert_txt_to_pdf(self, file_path: str) -> str:
        """Convert TXT to PDF"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            self.log("INFO", "Converting TXT to PDF")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            output_path = os.path.join(self.temp_dir, "converted_document.pdf")
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            # Split text into pages
            lines = text.split('\n')
            y = height - 40
            page_lines = 0
            
            for line in lines:
                if page_lines >= 50:  # ~50 lines per page
                    c.showPage()
                    y = height - 40
                    page_lines = 0
                
                c.drawString(40, y, line[:100])
                y -= 12
                page_lines += 1
            
            c.save()
            self.log("INFO", f"TXT converted to {output_path}")
            
            return output_path
        
        except Exception as e:
            self.error(f"TXT conversion failed: {str(e)}", e)
            raise
    
    async def _convert_json_to_pdf(self, file_path: str) -> str:
        """Convert JSON to formatted PDF"""
        try:
            import json
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            self.log("INFO", "Converting JSON to PDF")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            output_path = os.path.join(self.temp_dir, "converted_document.pdf")
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            y = height - 40
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            for line in json_str.split('\n'):
                c.drawString(40, y, line[:100])
                y -= 12
                if y < 40:
                    c.showPage()
                    y = height - 40
            
            c.save()
            self.log("INFO", f"JSON converted to {output_path}")
            
            return output_path
        
        except Exception as e:
            self.error(f"JSON conversion failed: {str(e)}", e)
            raise
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF for preview"""
        try:
            import PyPDF2
            
            text_content = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Extract text from first 2 pages
                pages_to_read = min(2, len(pdf_reader.pages))
                for page_num in range(pages_to_read):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text()
            
            self.log("INFO", "PDF text extracted")
            return text_content
        
        except Exception as e:
            self.log("WARNING", f"Could not extract PDF text: {str(e)}")
            return "Could not extract text preview"