"""
Base agent class - abstract interface for all agent types
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in the system"""
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique identifier for agent
            config: Configuration dictionary
        """
        self.agent_id = agent_id or str(uuid.uuid4())
        self.config = config or {}
        self.created_at = datetime.utcnow()
        self.last_run = None
        self.execution_count = 0
        self.errors = []
        self.logs = []
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with given input
        
        Args:
            input_data: Input data for agent
            
        Returns:
            Result dictionary with status and data
        """
        pass
    
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before execution
        
        Args:
            input_data: Input to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def log(self, level: str, message: str, metadata: Optional[Dict] = None):
        """
        Log a message
        
        Args:
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
            message: Log message
            metadata: Additional metadata
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "metadata": metadata or {}
        }
        self.logs.append(log_entry)
        
        # Also log to standard logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def error(self, message: str, exc: Optional[Exception] = None):
        """
        Record an error
        
        Args:
            message: Error message
            exc: Exception object
        """
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "exception": str(exc) if exc else None
        }
        self.errors.append(error_entry)
        self.log("ERROR", message, {"exception": str(exc) if exc else None})
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run agent with validation and error handling
        
        Args:
            input_data: Input data
            
        Returns:
            Execution result
        """
        try:
            # Validate input
            is_valid = await self.validate_input(input_data)
            if not is_valid:
                error_msg = "Input validation failed"
                self.error(error_msg)
                return {
                    "status": "error",
                    "agent_id": self.agent_id,
                    "message": error_msg,
                    "data": None
                }
            
            # Execute
            self.log("INFO", f"Executing agent {self.agent_id}")
            result = await self.execute(input_data)
            self.last_run = datetime.utcnow()
            self.execution_count += 1
            
            return result
        
        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            self.error(error_msg, e)
            return {
                "status": "error",
                "agent_id": self.agent_id,
                "message": error_msg,
                "data": None
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "execution_count": self.execution_count,
            "total_errors": len(self.errors),
            "total_logs": len(self.logs)
        }


class AgentChain:
    """Chain multiple agents together"""
    
    def __init__(self, agents: List[BaseAgent], chain_id: Optional[str] = None):
        """
        Initialize agent chain
        
        Args:
            agents: List of agents to chain
            chain_id: Unique identifier for chain
        """
        self.chain_id = chain_id or str(uuid.uuid4())
        self.agents = agents
        self.results = []
        self.created_at = datetime.utcnow()
    
    async def execute(self, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute chain of agents sequentially
        
        Args:
            initial_input: Initial input data
            
        Returns:
            Final result from chain
        """
        current_input = initial_input
        
        for i, agent in enumerate(self.agents):
            logger.info(f"Executing agent {i+1}/{len(self.agents)} - {agent.agent_id}")
            
            result = await agent.run(current_input)
            self.results.append(result)
            
            if result["status"] == "error":
                logger.error(f"Agent {i} failed: {result['message']}")
                return {
                    "status": "error",
                    "chain_id": self.chain_id,
                    "failed_at_agent": i,
                    "message": result["message"],
                    "results": self.results
                }
            
            # Pass result data to next agent
            current_input = result.get("data", current_input)
        
        return {
            "status": "success",
            "chain_id": self.chain_id,
            "results": self.results,
            "final_output": current_input
        }