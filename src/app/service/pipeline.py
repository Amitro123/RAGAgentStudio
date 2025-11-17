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

from agents.decision_agent import DecisionAgent
from agents.rag_agent import RAGAgent
from app.pipelines.basic_pipeline import Pipeline
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def rag_pipeline(initial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Defines and executes the RAG pipeline.

    Args:
        initial_data: The initial data for the pipeline.

    Returns:
        The result of the pipeline execution.
    """
    decision_agent = DecisionAgent()
    rag_agent = RAGAgent(api_key=settings.GEMINI_API_KEY)

    pipeline = Pipeline(agents=[decision_agent, rag_agent])

    result = await pipeline.execute(initial_input=initial_data)
    return result


# Global storage
processing_pipelines: Dict[str, ProcessingPipeline] = {}
