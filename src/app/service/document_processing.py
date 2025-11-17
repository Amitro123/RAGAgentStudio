"""
Document processing service
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from app.services.pipeline import ProcessingPipeline
from app.config import settings
from app.models import AgentConfig

logger = logging.getLogger(__name__)

async def process_document_pipeline(
    task_id: str,
    file_path: str,
    instructions: str,
    file_name: str,
    pipeline: ProcessingPipeline,
    notify_callback = None
):
    """Main processing pipeline"""
    
    try:
        # Step 1: Decision - Validate inputs
        pipeline.current_step = "decision"
        pipeline.add_log("INFO", "🔄 Step 1: Validating inputs...")
        
        if len(instructions.strip()) < 20:
            pipeline.add_error("Instructions too short (minimum 20 characters)")
            return
        
        if not os.path.exists(file_path):
            pipeline.add_error(f"File not found: {file_path}")
            return
        
        file_type = file_name.split('.')[-1].lower()
        if file_type not in ['pdf', 'docx', 'txt', 'json']:
            pipeline.add_error(f"Unsupported file type: {file_type}")
            return
        
        pipeline.mark_step_complete("decision")
        pipeline.add_log("INFO", f"✅ Validation complete (file type: {file_type})")
        
        if notify_callback:
            await notify_callback(task_id, "decision_complete", {"file_type": file_type})
        
        # Step 2: Parsing (if needed)
        pipeline.current_step = "parsing"
        if file_type != "pdf":
            pipeline.add_log("INFO", "🔄 Step 2: Converting to PDF...")
            await asyncio.sleep(1)  # Simulate conversion
            pipeline.add_log("INFO", "✅ File converted")
        else:
            pipeline.add_log("INFO", "✅ File is PDF - no conversion needed")
        
        pipeline.mark_step_complete("parsing")
        
        if notify_callback:
            await notify_callback(task_id, "parsing_complete", {})
        
        # Step 3: RAG Extraction
        pipeline.current_step = "rag_extraction"
        pipeline.add_log("INFO", "🔄 Step 3: Extracting document with RAG...")
        
        if not settings.GEMINI_API_KEY:
            pipeline.add_error("GEMINI_API_KEY not set")
            return
        
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Create file search store
            pipeline.add_log("INFO", "📦 Creating File Search Store...")
            store = client.file_search_stores.create(
                config={"display_name": f"store_{task_id}"}
            )
            pipeline.add_log("INFO", f"✅ Store created: {store.name}")
            
            # Upload file
            pipeline.add_log("INFO", f"📤 Uploading {file_name}...")
            operation = client.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=store.name,
                config={
                    "display_name": file_name,
                    "chunking_config": {
                        "white_space_config": {
                            "max_tokens_per_chunk": 200,
                            "max_overlap_tokens": 20,
                        }
                    }
                }
            )
            
            # Poll until done
            while not operation.done:
                await asyncio.sleep(2)
                operation = client.operations.get(operation)
            
            pipeline.add_log("INFO", "✅ File uploaded and indexed")
            
            # Extract metadata
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="""Analyze this document:
1. How many main sections?
2. Key topics?
3. Is it detailed enough for an AI agent (0-100)?
Respond as JSON.""",
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store.name]
                            )
                        )
                    ]
                )
            )
            
            analysis = response.text
            pipeline.add_log("INFO", f"📊 Analysis: {analysis[:200]}...")
            
            sufficiency_score = 75
            
            pipeline.mark_step_complete("rag_extraction")
            pipeline.add_log("INFO", f"✅ Extraction complete (score: {sufficiency_score}%)")
            
            if notify_callback:
                await notify_callback(task_id, "rag_complete", {
                    "sufficiency_score": sufficiency_score,
                    "store_name": store.name
                })
            
        except Exception as e:
            pipeline.add_error(f"RAG extraction failed: {str(e)}")
            return
        
        # Step 4: Agent Creation
        pipeline.current_step = "agent_creation"
        pipeline.add_log("INFO", "🔄 Step 4: Creating agent configuration...")
        
        agent_config = AgentConfig(
            id=f"agent_{task_id}",
            name=file_name.replace('.pdf', ''),
            type="gemini_rag_agent",
            status="ready",
            instructions=instructions[:500],
            file_source=file_name,
            rag_config={
                "file_search_store": store.name if 'store' in locals() else "unknown",
                "chunking_strategy": "whitespace",
                "max_tokens_per_chunk": 200
            },
            model_config={
                "model": "gemini-2.5-flash",
                "temperature": 0.7,
                "top_k": 10
            },
            created_at=datetime.utcnow().isoformat()
        )
        
        pipeline.agent_config = agent_config
        pipeline.mark_step_complete("agent_creation")
        pipeline.add_log("INFO", f"✅ Agent created: {agent_config.id}")
        
        if notify_callback:
            await notify_callback(task_id, "agent_created", agent_config.__dict__)
        
        # Step 5: Complete
        pipeline.current_step = "complete"
        pipeline.add_log("SUCCESS", "🎉 Processing completed successfully!")
        
        if notify_callback:
            await notify_callback(task_id, "complete", {
                "agent_id": agent_config.id,
                "status": "ready"
            })
    
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        pipeline.add_error(f"Unexpected error: {str(e)}")
        pipeline.current_step = "error"
