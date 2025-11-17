"""
RAG Agent - handles document extraction using Gemini File Search API
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
try:
    from google import genai
    from google.genai import exceptions
except ImportError:
    genai = None
    exceptions = None
import logging
try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


class GeminiApiError(Exception):
    """Custom exception for Gemini API errors."""

    pass


async def is_internet_available():
    """Check for internet connectivity."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.google.com", timeout=5)
            return response.status_code == 200
    except httpx.RequestError:
        return False


class RAGAgent(BaseAgent):
    """
    RAG (Retrieval Augmented Generation) Agent
    
    Uses Gemini File Search API to:
    1. Create file search store
    2. Upload and index documents
    3. Extract information with RAG
    4. Validate document sufficiency
    """
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "rag_agent"
        self.gemini_client = genai.Client(api_key=api_key)
        self.file_search_store = None
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate RAG input
        
        Expected input:
        {
            "file_path": str,
            "file_name": str,
            "instructions": str,
            "chunking_config": Optional[Dict]
        }
        """
        required_fields = ["file_path", "file_name"]
        
        for field in required_fields:
            if field not in input_data:
                self.log("WARNING", f"Missing required field: {field}")
                return False
        
        return True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute RAG extraction process
        
        Returns:
        {
            "status": "success" | "error",
            "file_search_store": str,
            "document_metadata": Dict,
            "extracted_info": Dict,
            "sufficiency_score": int
        }
        """
        if not await is_internet_available():
            raise GeminiApiError("No internet connection available.")

        try:
            file_path = input_data["file_path"]
            file_name = input_data["file_name"]
            instructions = input_data.get("instructions", "")

            self.log("INFO", f"Starting RAG extraction for {file_name}")

            store_name = await self._create_file_search_store(file_name)
            await self._upload_to_store(file_path, file_name)

            metadata = await self._extract_metadata(instructions)
            sufficiency = await self._validate_sufficiency(instructions)

            self.log("INFO", "RAG extraction completed successfully")

            return {
                "status": "success",
                "agent_id": self.agent_id,
                "data": {
                    "file_search_store": store_name,
                    "document_metadata": metadata,
                    "extracted_info": {
                        "analysis": sufficiency["analysis"],
                        "sections": metadata.get("total_sections", 0),
                        "key_topics": metadata.get("key_topics", []),
                    },
                    "sufficiency_score": sufficiency["score"],
                },
                "message": "Document extracted and indexed successfully",
            }
        except (exceptions.GoogleAPICallError, exceptions.RetryError) as e:
            raise GeminiApiError(f"Gemini API is currently unavailable: {e}")
    
    async def _create_file_search_store(self, store_name: str) -> str:
        """Create File Search Store"""
        try:
            self.log("INFO", f"Creating File Search Store: {store_name}")
            
            self.file_search_store = self.gemini_client.file_search_stores.create(
                config={"display_name": store_name}
            )
            
            self.log("INFO", f"Store created: {self.file_search_store.name}")
            return self.file_search_store.name
        
        except Exception as e:
            self.log("ERROR", f"Failed to create store: {str(e)}")
            raise
    
    async def _upload_to_store(
        self,
        file_path: str,
        file_name: str,
        chunking_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Upload file to File Search Store"""
        try:
            if not self.file_search_store:
                raise ValueError("File Search Store not initialized")
            
            self.log("INFO", f"Uploading file: {file_name}")
            
            if not chunking_config:
                chunking_config = {
                    "white_space_config": {
                        "max_tokens_per_chunk": 200,
                        "max_overlap_tokens": 20,
                    }
                }
            
            # Upload file
            operation = self.gemini_client.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=self.file_search_store.name,
                config={
                    "display_name": file_name,
                    "chunking_config": chunking_config,
                }
            )
            
            # Poll until upload completes
            max_retries = 60
            retry_count = 0
            
            while not operation.done and retry_count < max_retries:
                await asyncio.sleep(2)
                operation = self.gemini_client.operations.get(operation)
                retry_count += 1
                self.log("INFO", f"Upload in progress... ({retry_count*2}s)")
            
            if not operation.done:
                raise TimeoutError("Upload operation timed out")
            
            self.log("INFO", f"File uploaded successfully")
            return {
                "status": "success",
                "message": "File uploaded",
                "file_name": file_name
            }
        
        except Exception as e:
            self.log("ERROR", f"Upload failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _extract_metadata(self, query: str = "") -> Dict[str, Any]:
        """Extract document metadata using RAG"""
        try:
            self.log("INFO", "Extracting document metadata")
            
            metadata_query = """
            Analyze this document and provide:
            1. Total number of main sections/chapters
            2. Key topics covered
            3. Estimated total word count
            4. Primary language
            5. Document structure (outline)
            
            Respond in JSON format.
            """
            
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=metadata_query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.file_search_store.name]
                            )
                        )
                    ]
                )
            )
            
            response_text = response.text
            self.log("INFO", "Metadata extracted successfully")
            
            # Parse response (simplified - in production use more robust parsing)
            metadata = {
                "total_sections": self._extract_number(response_text, "section", 3),
                "key_topics": self._extract_topics(response_text),
                "estimated_words": self._extract_number(response_text, "word", 1000),
                "language": "he" if "עברית" in response_text or "עברי" in response_text else "en",
                "analysis": response_text[:500]
            }
            
            return metadata
        
        except Exception as e:
            self.log("WARNING", f"Metadata extraction failed: {str(e)}")
            return {
                "total_sections": 0,
                "key_topics": [],
                "estimated_words": 0,
                "language": "unknown"
            }
    
    async def _validate_sufficiency(self, instructions: str = "") -> Dict[str, Any]:
        """Validate document sufficiency for agent creation"""
        try:
            self.log("INFO", "Validating document sufficiency")
            
            validation_query = """
            Evaluate this document for creating an intelligent AI agent:
            1. Is the document detailed enough? (sections, subsections, examples)
            2. Does it have clear structure and hierarchy?
            3. Are there enough examples and use cases?
            4. Would an AI agent be able to understand and follow the instructions?
            5. What's the completeness score (0-100)?
            6. What additional information would help?
            
            Respond in structured format with clear scores.
            """
            
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.file_search_store.name]
                            )
                        )
                    ]
                )
            )
            
            response_text = response.text
            
            # Extract sufficiency score
            score = self._extract_score_from_response(response_text)
            
            # Extract grounding sources
            sources = []
            if response.candidates and response.candidates[0].grounding_metadata:
                grounding = response.candidates[0].grounding_metadata
                for chunk in grounding.grounding_chunks:
                    if hasattr(chunk, 'retrieved_context'):
                        sources.append({
                            "title": getattr(chunk.retrieved_context, 'title', 'Unknown'),
                            "section": getattr(chunk.retrieved_context, 'text', '')[:100]
                        })
            
            self.log("INFO", f"Sufficiency validation completed: score={score}")
            
            return {
                "is_sufficient": score >= 60,
                "score": score,
                "analysis": response_text,
                "sources": sources
            }
        
        except Exception as e:
            self.log("ERROR", f"Validation failed: {str(e)}")
            return {
                "is_sufficient": False,
                "score": 0,
                "analysis": str(e),
                "sources": []
            }
    
    def _extract_number(self, text: str, keyword: str, default: int = 0) -> int:
        """Extract number from text"""
        import re
        # Simple regex pattern to find numbers
        pattern = rf'(\d+)\s+{keyword}'
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return int(matches[0])
        return default
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from text"""
        # Simple extraction - returns common words
        topics = []
        keywords = ['process', 'procedure', 'policy', 'requirement', 'step', 'guideline']
        for keyword in keywords:
            if keyword.lower() in text.lower():
                topics.append(keyword)
        return topics[:5]  # Return max 5 topics
    
    def _extract_score_from_response(self, text: str) -> int:
        """Extract sufficiency score from AI response"""
        import re
        # Look for score patterns like "80", "80%", "80 out of 100"
        patterns = [
            r'(\d+)\s*%',
            r'(\d+)\s*/\s*100',
            r'score[:\s]+(\d+)',
            r'completeness[:\s]+(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score = int(matches[0])
                return min(100, max(0, score))
        
        # Default scoring based on keywords
        score = 50
        if any(word in text.lower() for word in ['complete', 'detailed', 'comprehensive']):
            score += 20
        if any(word in text.lower() for word in ['insufficient', 'lacking', 'missing']):
            score -= 20
        
        return min(100, max(0, score))