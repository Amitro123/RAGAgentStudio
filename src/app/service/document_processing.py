import asyncio
import logging
from typing import Dict, Any
from app.service.pipeline import rag_pipeline
from app.service.pipeline import ProcessingPipeline, processing_pipelines

logger = logging.getLogger(__name__)


async def process_document(
    task_id: str,
    file_path: str,
    instructions: str,
    file_name: str,
    notify_callback=None,
):
    """
    Main processing function to run the RAG pipeline.
    """
    pipeline = ProcessingPipeline(task_id=task_id)
    processing_pipelines[task_id] = pipeline

    try:
        pipeline.add_log("INFO", "Starting document processing pipeline...")

        initial_data = {
            "file_path": file_path,
            "file_name": file_name,
            "instructions": instructions,
        }

        result = await rag_pipeline(initial_data)

        if result.get("status") == "error":
            pipeline.add_error(result.get("message", "An unknown error occurred."))
            return

        pipeline.current_step = "complete"
        pipeline.add_log("SUCCESS", "🎉 Processing completed successfully!")

        if notify_callback:
            await notify_callback(task_id, "complete", result.get("final_context"))

    except Exception as e:
        logger.error(f"Pipeline error for task {task_id}: {e}")
        pipeline.add_error(str(e))
        pipeline.current_step = "error"
