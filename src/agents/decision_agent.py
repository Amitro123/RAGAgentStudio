"""
Decision Agent - validates inputs and decides next steps
"""
from typing import Dict, Any, Optional
from .base_agent import BaseAgent

import logging

logger = logging.getLogger(__name__)


class DecisionAgent(BaseAgent):
    """
    Decision-making agent that validates inputs and determines next steps
    
    Steps:
    1. Check if instructions are sufficient (length, detail)
    2. Check if file is provided
    3. Determine file type
    4. Make routing decision
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "decision_agent"
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data structure.

        Expected input (flexible):
        {
            "instructions": str,
            "file": File object or path (optional),
            "file_path": str (optional)
        }
        """
        # Only require instructions; file/file_path is handled in execute()
        if "instructions" not in input_data:
            self.log("WARNING", "Missing required field: instructions")
            return False

        return True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute decision logic
        
        Returns:
        {
            "status": "success" | "error",
            "decisions": {
                "instructions_valid": bool,
                "file_exists": bool,
                "file_type": str,
                "next_step": str,
                "requires_conversion": bool,
                "messages": List[str]
            }
        }
        """
        try:
            self.log("INFO", "Starting decision making process")
            
            decisions = {
                "instructions_valid": False,
                "file_exists": False,
                "file_type": None,
                "next_step": None,
                "requires_conversion": False,
                "messages": []
            }
            
            # 1. Validate instructions
            instructions = input_data.get("instructions", "").strip()
            min_instruction_length = 20
            
            if len(instructions) < min_instruction_length:
                decisions["messages"].append(
                    f"❌ Instructions too short (minimum {min_instruction_length} characters)"
                )
                self.log("WARNING", f"Instructions too short: {len(instructions)} chars")
            else:
                decisions["instructions_valid"] = True
                decisions["messages"].append(
                    f"✅ Instructions valid ({len(instructions)} characters)"
                )
                self.log("INFO", "Instructions validated")
            
            # 2. Check if file exists and get type (support both 'file' and 'file_path')
            file_obj = input_data.get("file") or input_data.get("file_path")

            if not file_obj:
                decisions["messages"].append("❌ No file provided")
                self.log("WARNING", "No file provided")
            else:
                decisions["file_exists"] = True
                
                # Determine file type
                file_type = self._determine_file_type(file_obj)
                decisions["file_type"] = file_type
                decisions["messages"].append(f"✅ File detected: {file_type.upper()}")
                self.log("INFO", f"File type detected: {file_type}")
                
                # Check if conversion needed
                if file_type != "pdf":
                    decisions["requires_conversion"] = True
                    decisions["messages"].append(
                        f"⚠️ {file_type.upper()} file - conversion to PDF required"
                    )
                    self.log("INFO", f"Conversion required: {file_type} -> pdf")
                else:
                    decisions["messages"].append("✅ PDF format - no conversion needed")
            
            # 3. Decide next step
            if decisions["instructions_valid"] and decisions["file_exists"]:
                if decisions["requires_conversion"]:
                    decisions["next_step"] = "parse_to_pdf"
                else:
                    decisions["next_step"] = "extract_with_rag"
                decisions["messages"].append(
                    f"🎯 Next step: {decisions['next_step']}"
                )
            else:
                decisions["next_step"] = "request_more_info"
                decisions["messages"].append(
                    "❌ Cannot proceed - missing required information"
                )
            
            self.log("INFO", "Decision making completed", decisions)
            
            return {
                "status": "success",
                "agent_id": self.agent_id,
                "data": decisions,
                "message": "Decision making process completed"
            }
        
        except Exception as e:
            self.error(f"Decision making failed: {str(e)}", e)
            return {
                "status": "error",
                "agent_id": self.agent_id,
                "message": str(e),
                "data": None
            }
    
    def _determine_file_type(self, file_obj: Any) -> str:
        """
        Determine file type from file object or path
        
        Args:
            file_obj: File object or path string
            
        Returns:
            File type (pdf, docx, txt, json)
        """
        # If it's a string path
        if isinstance(file_obj, str):
            path = file_obj.lower()
            if path.endswith('.pdf'):
                return "pdf"
            elif path.endswith(('.docx', '.doc')):
                return "docx"
            elif path.endswith('.txt'):
                return "txt"
            elif path.endswith('.json'):
                return "json"
        
        # If it's a file object
        if hasattr(file_obj, 'filename'):
            filename = file_obj.filename.lower()
            if filename.endswith('.pdf'):
                return "pdf"
            elif filename.endswith(('.docx', '.doc')):
                return "docx"
            elif filename.endswith('.txt'):
                return "txt"
            elif filename.endswith('.json'):
                return "json"
        
        # If it has content_type attribute
        if hasattr(file_obj, 'content_type'):
            content_type = file_obj.content_type.lower()
            if 'pdf' in content_type:
                return "pdf"
            elif 'word' in content_type or 'document' in content_type:
                return "docx"
            elif 'text' in content_type:
                return "txt"
            elif 'json' in content_type:
                return "json"
        
        return "unknown"
    
    def get_decision_summary(self, decisions: Dict[str, Any]) -> str:
        """
        Get human-readable summary of decisions
        
        Args:
            decisions: Decisions dict
            
        Returns:
            Summary string
        """
        summary_parts = [
            f"Instructions: {'✅ Valid' if decisions['instructions_valid'] else '❌ Invalid'}",
            f"File: {'✅ Present' if decisions['file_exists'] else '❌ Missing'}",
            f"File Type: {decisions['file_type'].upper() if decisions['file_type'] else 'Unknown'}",
            f"Conversion Needed: {'Yes' if decisions['requires_conversion'] else 'No'}",
            f"Next Step: {decisions['next_step']}"
        ]
        return " | ".join(summary_parts)