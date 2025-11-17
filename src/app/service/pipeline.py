"""
Processing pipeline management
"""
from datetime import datetime
from typing import Dict, Optional, Any, List
from app.models import LogEntry, AgentConfig

class ProcessingPipeline:
    """Processing pipeline state manager"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.agent_config: Optional[AgentConfig] = None
        self.current_step = "upload"
        self.steps_completed: List[str] = []
        self.logs: List[LogEntry] = []
        self.errors: List[str] = []
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_log(self, level: str, message: str, metadata: Optional[Dict] = None):
        """Add log entry"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
            metadata=metadata or {}
        )
        self.logs.append(log_entry)
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error: str):
        """Add error"""
        self.errors.append(error)
        self.add_log("ERROR", error)
    
    def mark_step_complete(self, step: str):
        """Mark step complete"""
        self.steps_completed.append(step)
        self.updated_at = datetime.utcnow()
    
    def get_progress(self) -> Dict[str, Any]:
        """Calculate progress"""
        total_steps = 5
        completed = len(self.steps_completed)
        return {
            "completed": completed,
            "total": total_steps,
            "percentage": (completed / total_steps) * 100
        }

# Global storage
processing_pipelines: Dict[str, ProcessingPipeline] = {}
