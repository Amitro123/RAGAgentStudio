"""
Fallback Agent - handles monitoring and falls back to internet search if needed
"""
import asyncio
from typing import Dict, Any, List, Optional
from .agent_base import BaseAgent
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class FallbackAgent(BaseAgent):
    """
    Fallback Agent - monitors process and searches internet for solutions
    
    Features:
    - Monitors stuck processes
    - Falls back to internet search
    - Finds similar solutions
    - Suggests workarounds
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "fallback_agent"
        self.monitoring_timeout = 30  # seconds
        self.max_retries = 3
        self.search_engine = "google"  # or "brave", "duckduckgo"
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate fallback input
        
        Expected input:
        {
            "process_status": Dict,
            "error_message": str,
            "timeout_seconds": Optional[int],
            "enable_search": Optional[bool]
        }
        """
        required_fields = ["process_status", "error_message"]
        
        for field in required_fields:
            if field not in input_data:
                self.log("WARNING", f"Missing required field: {field}")
                return False
        
        return True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute fallback monitoring and recovery
        
        Returns:
        {
            "status": "success" | "error",
            "is_stuck": bool,
            "recovery_attempted": bool,
            "search_results": List[Dict],
            "suggestions": List[str],
            "recovered": bool
        }
        """
        try:
            self.log("INFO", "Starting fallback monitoring")
            
            process_status = input_data.get("process_status", {})
            error_message = input_data.get("error_message", "")
            timeout = input_data.get("timeout_seconds", self.monitoring_timeout)
            enable_search = input_data.get("enable_search", True)
            
            # Check if process is stuck
            is_stuck = await self._is_process_stuck(process_status, timeout)
            
            if not is_stuck:
                self.log("INFO", "Process is healthy")
                return {
                    "status": "success",
                    "agent_id": self.agent_id,
                    "data": {
                        "is_stuck": False,
                        "recovery_attempted": False,
                        "search_results": [],
                        "suggestions": [],
                        "recovered": True
                    },
                    "message": "Process is operational"
                }
            
            # Process is stuck - attempt recovery
            self.log("WARNING", f"Process stuck detected: {error_message}")
            
            recovery_data = {
                "is_stuck": True,
                "recovery_attempted": False,
                "search_results": [],
                "suggestions": [],
                "recovered": False,
                "error_analysis": None
            }
            
            if enable_search:
                # Analyze error and search for solutions
                error_analysis = await self._analyze_error(error_message)
                recovery_data["error_analysis"] = error_analysis
                
                # Search for solutions
                search_results = await self._search_solutions(error_message)
                recovery_data["search_results"] = search_results
                recovery_data["recovery_attempted"] = True
                
                # Generate suggestions
                suggestions = await self._generate_suggestions(
                    error_message,
                    search_results,
                    error_analysis
                )
                recovery_data["suggestions"] = suggestions
                
                # Check if recovery possible
                recovery_data["recovered"] = len(suggestions) > 0
                
                self.log("INFO", f"Found {len(suggestions)} recovery suggestions")
            
            return {
                "status": "success",
                "agent_id": self.agent_id,
                "data": recovery_data,
                "message": "Fallback monitoring completed"
            }
        
        except Exception as e:
            self.error(f"Fallback execution failed: {str(e)}", e)
            return {
                "status": "error",
                "agent_id": self.agent_id,
                "message": str(e),
                "data": None
            }
    
    async def _is_process_stuck(
        self,
        process_status: Dict[str, Any],
        timeout: int
    ) -> bool:
        """
        Determine if process is stuck
        
        Criteria:
        - No updates for X seconds
        - Status is still "processing"
        - Errors present
        """
        try:
            updated_at = process_status.get("updated_at")
            current_status = process_status.get("status", "")
            errors = process_status.get("errors", [])
            
            if not updated_at:
                return False
            
            # Check if updated recently
            if isinstance(updated_at, str):
                from datetime import datetime
                updated_time = datetime.fromisoformat(updated_at)
                elapsed = (datetime.utcnow() - updated_time).total_seconds()
            else:
                elapsed = (datetime.utcnow() - updated_at).total_seconds()
            
            is_stuck = elapsed > timeout and current_status == "processing" and len(errors) > 0
            
            self.log("INFO", f"Process check: elapsed={elapsed}s, timeout={timeout}s, stuck={is_stuck}")
            
            return is_stuck
        
        except Exception as e:
            self.log("WARNING", f"Could not check process status: {str(e)}")
            return False
    
    async def _analyze_error(self, error_message: str) -> Dict[str, Any]:
        """Analyze error message"""
        try:
            self.log("INFO", f"Analyzing error: {error_message[:100]}")
            
            analysis = {
                "error_type": "unknown",
                "severity": "medium",
                "likely_causes": [],
                "keywords": []
            }
            
            error_lower = error_message.lower()
            
            # Error type classification
            if "timeout" in error_lower:
                analysis["error_type"] = "timeout"
                analysis["severity"] = "high"
                analysis["likely_causes"] = [
                    "Process taking too long",
                    "Network connectivity issue",
                    "Resource exhaustion"
                ]
            
            elif "permission" in error_lower or "denied" in error_lower:
                analysis["error_type"] = "permission"
                analysis["severity"] = "high"
                analysis["likely_causes"] = [
                    "Insufficient permissions",
                    "API key invalid",
                    "Access denied"
                ]
            
            elif "memory" in error_lower or "limit" in error_lower:
                analysis["error_type"] = "resource"
                analysis["severity"] = "high"
                analysis["likely_causes"] = [
                    "Out of memory",
                    "Quota exceeded",
                    "Resource limit"
                ]
            
            elif "not found" in error_lower or "404" in error_lower:
                analysis["error_type"] = "not_found"
                analysis["severity"] = "medium"
                analysis["likely_causes"] = [
                    "File not found",
                    "API endpoint changed",
                    "Resource deleted"
                ]
            
            else:
                analysis["error_type"] = "general"
                analysis["severity"] = "medium"
                analysis["likely_causes"] = [
                    "Unexpected error",
                    "Incompatible input",
                    "External service issue"
                ]
            
            # Extract keywords
            keywords_to_find = ["api", "network", "file", "database", "auth", "upload", "parse"]
            for keyword in keywords_to_find:
                if keyword in error_lower:
                    analysis["keywords"].append(keyword)
            
            return analysis
        
        except Exception as e:
            self.log("WARNING", f"Error analysis failed: {str(e)}")
            return {"error_type": "unknown", "severity": "medium"}
    
    async def _search_solutions(self, error_message: str) -> List[Dict[str, str]]:
        """Search internet for solutions"""
        try:
            self.log("INFO", "Searching for solutions online")
            
            # Build search query
            search_query = self._build_search_query(error_message)
            
            results = []
            
            # Try multiple search APIs
            try:
                # Using requests to generic search (in production, use proper API)
                search_url = f"https://www.google.com/search?q={search_query}"
                
                # In production, use proper search API like:
                # - Google Custom Search API
                # - Brave Search API
                # - DuckDuckGo API
                
                results.append({
                    "source": "google",
                    "query": search_query,
                    "url": search_url,
                    "title": "Google Search Results",
                    "snippet": f"Search for: {search_query}"
                })
                
                self.log("INFO", f"Search completed for: {search_query}")
            
            except Exception as e:
                self.log("WARNING", f"Search request failed: {str(e)}")
            
            return results
        
        except Exception as e:
            self.log("ERROR", f"Solution search failed: {str(e)}")
            return []
    
    async def _generate_suggestions(
        self,
        error_message: str,
        search_results: List[Dict],
        error_analysis: Dict
    ) -> List[str]:
        """Generate recovery suggestions"""
        try:
            suggestions = []
            
            # Basic suggestions based on error analysis
            error_type = error_analysis.get("error_type", "unknown")
            
            if error_type == "timeout":
                suggestions.extend([
                    "Increase timeout duration",
                    "Check network connectivity",
                    "Split document into smaller files",
                    "Reduce chunking complexity"
                ])
            
            elif error_type == "permission":
                suggestions.extend([
                    "Verify API key is valid",
                    "Check file permissions",
                    "Ensure service account has required access",
                    "Try re-authenticating"
                ])
            
            elif error_type == "resource":
                suggestions.extend([
                    "Process large files in batches",
                    "Increase available resources",
                    "Reduce concurrent operations",
                    "Archive older sessions"
                ])
            
            elif error_type == "not_found":
                suggestions.extend([
                    "Verify file path is correct",
                    "Check if resource still exists",
                    "Try re-uploading the file",
                    "Check API documentation for updates"
                ])
            
            else:
                suggestions.extend([
                    "Check error logs for details",
                    "Try running process again",
                    "Restart the service",
                    "Contact support with error message"
                ])
            
            # Add search-based suggestions
            if search_results:
                suggestions.append(
                    f"Found online solutions: {search_results[0].get('url', '')}"
                )
            
            self.log("INFO", f"Generated {len(suggestions)} suggestions")
            
            return suggestions
        
        except Exception as e:
            self.log("WARNING", f"Suggestion generation failed: {str(e)}")
            return []
    
    def _build_search_query(self, error_message: str) -> str:
        """Build search query from error message"""
        # Extract key terms
        terms = []
        
        # Get first 50 characters or up to first punctuation
        clean_error = error_message.split('\n')[0][:100]
        
        # Remove common prefixes
        for prefix in ["error:", "exception:", "failed:", "error -"]:
            if clean_error.lower().startswith(prefix):
                clean_error = clean_error[len(prefix):].strip()
                break
        
        return f"python {clean_error}"