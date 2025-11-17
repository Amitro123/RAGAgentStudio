"""
Data models and Pydantic schemas for the Agent Builder Platform
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class FileTypeEnum(str, Enum):
    """Supported file types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    JSON = "json"


class AgentStatusEnum(str, Enum):
    """Agent status states"""
    PENDING = "pending"
    PROCESSING = "processing"
    VALIDATING = "validating"
    READY = "ready"
    DEPLOYED = "deployed"
    ERROR = "error"
    ARCHIVED = "archived"


class ChunkingStrategyEnum(str, Enum):
    """Document chunking strategies"""
    WHITESPACE = "whitespace"
    SEMANTIC = "semantic"
    FIXED_SIZE = "fixed_size"


# ==================== Request/Response Models ====================

class FileUploadRequest(BaseModel):
    """Request model for file upload"""
    instructions: str = Field(
        ..., 
        min_length=20, 
        max_length=5000,
        description="Detailed instructions for the agent"
    )
    file_name: str = Field(..., description="Original file name")
    file_type: FileTypeEnum = Field(..., description="Type of file")
    
    @validator('instructions')
    def instructions_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Instructions cannot be empty')
        return v.strip()


class DocumentMetadata(BaseModel):
    """Metadata extracted from document"""
    total_pages: int
    total_words: int
    total_sections: int
    key_topics: List[str]
    language: str = "he"
    file_size_mb: float
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class RAGConfig(BaseModel):
    """RAG configuration for agent"""
    file_search_store: str = Field(..., description="Gemini File Search store name")
    chunking_strategy: ChunkingStrategyEnum = ChunkingStrategyEnum.WHITESPACE
    max_tokens_per_chunk: int = Field(default=200, ge=100, le=1000)
    overlap_tokens: int = Field(default=20, ge=0, le=100)
    embedding_model: str = "text-embedding-004"


class ModelConfig(BaseModel):
    """LLM model configuration"""
    model: str = "gemini-2.5-flash"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_k: int = Field(default=10, ge=1, le=50)
    max_output_tokens: int = Field(default=2048, ge=100, le=4096)


class AgentConfig(BaseModel):
    """Complete agent configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., max_length=255)
    instructions: str = Field(..., max_length=5000)
    file_source: str
    file_type: FileTypeEnum
    status: AgentStatusEnum = AgentStatusEnum.PENDING
    rag_config: RAGConfig
    model_config: ModelConfig
    document_metadata: Optional[DocumentMetadata] = None
    sufficiency_score: int = Field(default=0, ge=0, le=100)
    is_sufficient: bool = False
    n8n_flow_id: Optional[str] = None
    mindsdb_kb_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deployed_at: Optional[datetime] = None


class AgentCreationRequest(BaseModel):
    """Request to create an agent"""
    agent_name: str = Field(..., max_length=255)
    instructions: str = Field(..., max_length=5000)
    file_path: str = Field(..., description="Path to uploaded file")
    file_type: FileTypeEnum
    model_config: Optional[ModelConfig] = None
    chunking_strategy: Optional[ChunkingStrategyEnum] = None


class ValidationResult(BaseModel):
    """Result of document validation"""
    is_sufficient: bool
    sufficiency_score: int
    analysis: str
    suggestions: List[str] = []
    metadata: Optional[DocumentMetadata] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExportFormat(str, Enum):
    """Export format options"""
    JSON = "json"
    N8N = "n8n"
    MINDSDB = "mindsdb"
    YAML = "yaml"


class ExportRequest(BaseModel):
    """Request to export agent config"""
    agent_id: str
    format: ExportFormat = ExportFormat.JSON
    include_metadata: bool = True


class AgentResponse(BaseModel):
    """Response with agent data"""
    agent: AgentConfig
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProcessingStatus(BaseModel):
    """Real-time processing status"""
    task_id: str
    step: int
    total_steps: int
    current_step_name: str
    progress_percentage: int
    status: str
    message: str
    errors: List[str] = []
    started_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LogEntry(BaseModel):
    """Log entry for processing"""
    level: str  # INFO, WARNING, ERROR, SUCCESS
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class N8nFlowConfig(BaseModel):
    """n8n workflow configuration"""
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    metadata: Dict[str, Any]


class MindsDBKnowledgeBase(BaseModel):
    """MindsDB knowledge base configuration"""
    knowledge_base_name: str
    source: str  # File Search Store name
    type: str = "gemini_file_search"
    config: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InternetSearchFallback(BaseModel):
    """Fallback search configuration"""
    is_enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    search_query: str = ""
    results: Optional[List[Dict[str, str]]] = None


class ProcessingPipeline(BaseModel):
    """Complete processing pipeline state"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_config: Optional[AgentConfig] = None
    current_step: str = "upload"
    steps_completed: List[str] = []
    logs: List[LogEntry] = []
    errors: List[str] = []
    fallback_searches: List[InternetSearchFallback] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_log(self, level: str, message: str, metadata: Optional[Dict] = None):
        """Add log entry to pipeline"""
        self.logs.append(LogEntry(
            level=level,
            message=message,
            task_id=self.task_id,
            metadata=metadata
        ))
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error: str):
        """Add error to pipeline"""
        self.errors.append(error)
        self.add_log("ERROR", error)
    
    def mark_step_complete(self, step: str):
        """Mark step as completed"""
        self.steps_completed.append(step)
        self.updated_at = datetime.utcnow()