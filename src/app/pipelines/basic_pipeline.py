from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import datetime
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Executes a sequence of agents, where each agent's output
    is stored in a shared context dictionary.
    """

    def __init__(self, agents: List[BaseAgent], pipeline_id: Optional[str] = None):
        self.pipeline_id = pipeline_id or str(uuid.uuid4())
        self.agents = agents
        self.context: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()

    async def execute(self, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the pipeline of agents.

        Args:
            initial_input: The initial data to pass to the first agent.

        Returns:
            The final context after all agents have run.
        """
        self.context = initial_input

        for i, agent in enumerate(self.agents):
            agent_name = agent.__class__.__name__
            logger.info(f"Executing agent {i + 1}/{len(self.agents)}: {agent_name}")

            result = await agent.run(self.context)

            if result.get("status") == "error":
                logger.error(f"Agent {agent_name} failed: {result.get('message')}")
                return {
                    "status": "error",
                    "pipeline_id": self.pipeline_id,
                    "failed_at_agent": i,
                    "agent_name": agent_name,
                    "message": result.get("message"),
                    "context": self.context,
                }

            # Update context with the result from the agent
            self.context.update(result.get("data", {}))

        return {
            "status": "success",
            "pipeline_id": self.pipeline_id,
            "final_context": self.context,
        }
