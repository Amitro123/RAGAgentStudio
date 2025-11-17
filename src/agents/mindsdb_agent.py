"""
MindsDB Agent - handles agent registration and deployment with MindsDB
"""
import json
from typing import Dict, Any, Optional
from .agent_base import BaseAgent
import logging
import requests

logger = logging.getLogger(__name__)


class MindsDBAgent(BaseAgent):
    """
    MindsDB Integration Agent
    
    Responsibilities:
    - Create agent configuration
    - Register with MindsDB
    - Generate n8n flow
    - Store agent metadata
    """
    
    def __init__(self, mindsdb_host: str = "http://localhost:47334", **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "mindsdb_agent"
        self.mindsdb_host = mindsdb_host
        self.api_version = "v1"
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate agent creation input
        
        Expected input:
        {
            "agent_name": str,
            "instructions": str,
            "file_source": str,
            "file_search_store": str,
            "sufficiency_score": int,
            "model_config": Optional[Dict]
        }
        """
        required_fields = [
            "agent_name",
            "instructions",
            "file_source",
            "file_search_store",
            "sufficiency_score"
        ]
        
        for field in required_fields:
            if field not in input_data:
                self.log("WARNING", f"Missing required field: {field}")
                return False
        
        if input_data.get("sufficiency_score", 0) < 50:
            self.log("WARNING", "Document may not have sufficient information")
        
        return True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent creation and registration
        
        Returns:
        {
            "status": "success" | "error",
            "agent_id": str,
            "agent_config": Dict,
            "n8n_flow": Dict,
            "mindsdb_registered": bool,
            "export_formats": Dict
        }
        """
        try:
            self.log("INFO", "Starting agent creation process")
            
            # Extract input
            agent_name = input_data.get("agent_name")
            instructions = input_data.get("instructions")
            file_source = input_data.get("file_source")
            file_search_store = input_data.get("file_search_store")
            sufficiency_score = input_data.get("sufficiency_score", 0)
            model_config = input_data.get("model_config")
            
            # Create agent config
            agent_config = self._create_agent_config(
                agent_name,
                instructions,
                file_source,
                file_search_store,
                sufficiency_score,
                model_config
            )
            
            self.log("INFO", f"Agent config created: {agent_config['id']}")
            
            # Create n8n flow
            n8n_flow = self._create_n8n_flow(agent_config)
            self.log("INFO", "n8n flow generated")
            
            # Try to register with MindsDB
            mindsdb_registered = False
            try:
                await self._register_with_mindsdb(agent_config)
                mindsdb_registered = True
                self.log("INFO", "Agent registered with MindsDB")
            except Exception as e:
                self.log("WARNING", f"MindsDB registration skipped: {str(e)}")
            
            # Create export formats
            export_formats = self._create_export_formats(agent_config, n8n_flow)
            
            self.log("INFO", "Agent creation completed successfully")
            
            return {
                "status": "success",
                "agent_id": self.agent_id,
                "data": {
                    "agent_id": agent_config["id"],
                    "agent_config": agent_config,
                    "n8n_flow": n8n_flow,
                    "mindsdb_registered": mindsdb_registered,
                    "export_formats": export_formats
                },
                "message": "Agent created successfully"
            }
        
        except Exception as e:
            self.error(f"Agent creation failed: {str(e)}", e)
            return {
                "status": "error",
                "agent_id": self.agent_id,
                "message": str(e),
                "data": None
            }
    
    def _create_agent_config(
        self,
        agent_name: str,
        instructions: str,
        file_source: str,
        file_search_store: str,
        sufficiency_score: int,
        model_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create agent configuration"""
        
        if not model_config:
            model_config = {
                "model": "gemini-2.5-flash",
                "temperature": 0.7,
                "top_k": 10,
                "max_output_tokens": 2048
            }
        
        config = {
            "id": f"agent_{self._generate_id()}",
            "name": agent_name,
            "type": "gemini_rag_agent",
            "status": "ready",
            "instructions": instructions,
            "file_source": file_source,
            "rag_config": {
                "file_search_store": file_search_store,
                "chunking_strategy": "whitespace",
                "max_tokens_per_chunk": 200,
                "overlap_tokens": 20,
                "embedding_model": "text-embedding-004"
            },
            "model_config": model_config,
            "metadata": {
                "sufficiency_score": sufficiency_score,
                "created_by": "agent_builder",
                "version": "1.0"
            },
            "capabilities": self._infer_capabilities(instructions)
        }
        
        return config
    
    def _create_n8n_flow(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create n8n workflow configuration"""
        
        flow = {
            "name": agent_config["name"],
            "description": f"AI Agent: {agent_config['name']}",
            "nodes": [
                {
                    "name": "Trigger",
                    "type": "n8n-nodes-base.webhookTrigger",
                    "position": [100, 100],
                    "parameters": {
                        "path": f"agent/{agent_config['id']}"
                    }
                },
                {
                    "name": "Gemini Query",
                    "type": "n8n-nodes-base.httpRequest",
                    "position": [350, 100],
                    "parameters": {
                        "authentication": "oAuth2",
                        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                        "method": "POST",
                        "bodyParametersUi": "json",
                        "body": json.dumps({
                            "contents": [{"parts": [{"text": "{{ $json.query }}"}]}],
                            "systemInstruction": agent_config["instructions"],
                            "tools": [{
                                "googleSearch": {
                                    "fileSearchStore": agent_config["rag_config"]["file_search_store"]
                                }
                            }],
                            "generationConfig": {
                                "temperature": agent_config["model_config"]["temperature"],
                                "topK": agent_config["model_config"]["top_k"],
                                "maxOutputTokens": agent_config["model_config"]["max_output_tokens"]
                            }
                        })
                    }
                },
                {
                    "name": "Response",
                    "type": "n8n-nodes-base.respondToWebhook",
                    "position": [600, 100],
                    "parameters": {
                        "responseCode": 200,
                        "responseData": {
                            "response": "{{ $json.candidates[0].content.parts[0].text }}"
                        }
                    }
                }
            ],
            "connections": {
                "Trigger": {
                    "main": [
                        [{"node": "Gemini Query", "type": "main", "index": 0}]
                    ]
                },
                "Gemini Query": {
                    "main": [
                        [{"node": "Response", "type": "main", "index": 0}]
                    ]
                }
            },
            "metadata": {
                "agent_id": agent_config["id"],
                "created_at": self._get_timestamp(),
                "rag_config": agent_config["rag_config"]
            }
        }
        
        return flow
    
    async def _register_with_mindsdb(self, agent_config: Dict[str, Any]) -> bool:
        """Register agent with MindsDB"""
        try:
            self.log("INFO", "Registering with MindsDB")
            
            kb_data = {
                "knowledge_base_name": agent_config["name"],
                "source": agent_config["rag_config"]["file_search_store"],
                "type": "gemini_file_search",
                "config": {
                    "agent_id": agent_config["id"],
                    "instructions": agent_config["instructions"],
                    "model_config": agent_config["model_config"]
                }
            }
            
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                f"{self.mindsdb_host}/api/{self.api_version}/knowledge_bases",
                json=kb_data,
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            self.log("INFO", "Successfully registered with MindsDB")
            
            return True
        
        except requests.exceptions.ConnectionError:
            self.log("WARNING", "Could not connect to MindsDB")
            return False
        except Exception as e:
            self.log("WARNING", f"MindsDB registration failed: {str(e)}")
            return False
    
    def _create_export_formats(
        self,
        agent_config: Dict[str, Any],
        n8n_flow: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create export formats"""
        
        exports = {}
        
        # JSON export
        exports["json"] = json.dumps({
            "agent": agent_config,
            "n8n_flow": n8n_flow,
            "export_date": self._get_timestamp()
        }, indent=2)
        
        # YAML export
        exports["yaml"] = self._to_yaml(agent_config)
        
        # n8n export
        exports["n8n"] = json.dumps(n8n_flow, indent=2)
        
        return exports
    
    def _infer_capabilities(self, instructions: str) -> list:
        """Infer agent capabilities from instructions"""
        capabilities = ["question_answering", "document_analysis"]
        
        keywords_to_capabilities = {
            "summarize": "summarization",
            "extract": "extraction",
            "categorize": "categorization",
            "generate": "content_generation",
            "translate": "translation",
            "analyze": "analysis",
            "recommend": "recommendation"
        }
        
        instructions_lower = instructions.lower()
        for keyword, capability in keywords_to_capabilities.items():
            if keyword in instructions_lower:
                capabilities.append(capability)
        
        return list(set(capabilities))
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import time
        return str(int(time.time() * 1000))[-8:]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def _to_yaml(self, data: Dict) -> str:
        """Convert dict to YAML format (simple version)"""
        def dict_to_yaml(d, indent=0):
            yaml_str = ""
            for key, value in d.items():
                if isinstance(value, dict):
                    yaml_str += "  " * indent + f"{key}:\n"
                    yaml_str += dict_to_yaml(value, indent + 1)
                elif isinstance(value, list):
                    yaml_str += "  " * indent + f"{key}:\n"
                    for item in value:
                        if isinstance(item, dict):
                            yaml_str += dict_to_yaml(item, indent + 1)
                        else:
                            yaml_str += "  " * (indent + 1) + f"- {item}\n"
                else:
                    yaml_str += "  " * indent + f"{key}: {value}\n"
            return yaml_str
        
        return dict_to_yaml(data)