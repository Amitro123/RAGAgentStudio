import logging
import uuid
import os
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.utils.logger import setup_logging
from app.service.document_processing import process_document
from app.service.pipeline import processing_pipelines

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAGAgent Studio",
    description="Build AI agents from PDF documents with Gemini File Search",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/upload-and-process")
async def upload_and_process(
    instructions: str = Form(...), file: UploadFile = File(...)
):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    asyncio.create_task(
        process_document(
            task_id=task_id,
            file_path=file_path,
            instructions=instructions,
            file_name=file.filename,
        )
    )

    return {
        "status": "processing_started",
        "task_id": task_id,
        "poll_url": f"/api/v1/status/{task_id}",
    }


@app.get("/api/v1/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in processing_pipelines:
        raise HTTPException(status_code=404, detail="Task not found")
    return processing_pipelines[task_id]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
