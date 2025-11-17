# 🤖 Agent Builder Platform

**Build intelligent AI agents automatically from PDF documents using Gemini File Search API and MindsDB.**

## 🎯 Overview

Agent Builder Platform is a comprehensive system that:
- ✅ Accepts PDF documents with detailed instructions
- ✅ Validates document quality and completeness
- ✅ Extracts and indexes content with Gemini File Search API
- ✅ Creates intelligent agents configured for your specific use case
- ✅ Exports agents to multiple formats (JSON, n8n, MindsDB)
- ✅ Provides fallback mechanisms with internet search capabilities

## 🏗️ Project Structure

```
project-root/
├── main.py                 # FastAPI server (entry point)
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── README.md              # Documentation
│
└── uploads/               # Uploaded files directory (created automatically)
```

**Simple flat structure** - everything in one directory for easy deployment!

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Google Gemini API key
- MindsDB (optional, for knowledge base registration)

### Installation

1. **Get Gemini API Key**
   - Go to: https://ai.google.dev/
   - Create a project
   - Enable Generative AI API
   - Create API key

2. **Setup Environment**
```bash
# Clone and enter directory
git clone <repo-url>
cd agent-builder-platform

# Create .env file
cp .env.example .env

# Edit .env with your API key
# GEMINI_API_KEY=your-key-here
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Run Server**
```bash
python main.py
```

Server will start at `http://localhost:8000`

5. **Access API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📋 Workflow

### Step 1: Upload & Validation
- User provides detailed instructions
- User uploads PDF document
- System validates inputs

### Step 2: File Processing
- Detects file format
- Converts to PDF if needed (DOCX, TXT, JSON)
- Preserves original content

### Step 3: Document Analysis (RAG)
- Creates Gemini File Search Store
- Uploads and indexes document
- Extracts metadata
- Validates document sufficiency (score 0-100)

### Step 4: Agent Creation
- Generates agent configuration
- Links to RAG file store
- Sets up model parameters
- Generates n8n workflow

### Step 5: Monitoring & Fallback
- Monitors agent creation
- Provides internet search fallback if stuck
- Suggests workarounds
- Returns export formats

## 🔧 API Endpoints

### Upload & Process
```bash
POST /api/v1/upload-and-process
Content-Type: multipart/form-data

Parameters:
- instructions: str (required, min 20 chars)
- file: UploadFile (required, max 100MB)

Response:
{
  "status": "processing_started",
  "task_id": "uuid",
  "poll_url": "/api/v1/status/{task_id}"
}
```

### Get Status
```bash
GET /api/v1/status/{task_id}

Response:
{
  "task_id": "uuid",
  "current_step": "rag_extraction",
  "steps_completed": ["decision", "parsing"],
  "progress": {
    "completed": 2,
    "total": 5,
    "percentage": 40
  },
  "logs": [...],
  "agent_config": {...}
}
```

### WebSocket for Real-Time Updates
```bash
WebSocket /ws/status/{task_id}
```

### Export Agent
```bash
POST /api/v1/export/{task_id}?format=json
# formats: json, n8n, yaml

Response: Agent configuration in requested format
```

## 📊 Agent Architecture

### Decision Agent
- Validates instructions quality
- Checks file presence
- Determines file type
- Routes to appropriate processor

### Parse Agent
- Handles file format conversion
- Supports: DOCX, TXT, JSON → PDF
- Extracts text preview

### RAG Agent
- Creates File Search Store
- Uploads and indexes document
- Extracts metadata
- Validates document sufficiency
- Cost: $0.15 per 1M tokens (indexing)

### MindsDB Agent
- Creates agent configuration
- Generates n8n flow
- Registers with MindsDB (optional)
- Exports to multiple formats

### Fallback Agent
- Monitors processing status
- Detects stuck processes
- Searches internet for solutions
- Suggests recovery steps

## 🔗 Integration Examples

### n8n Integration
Export agent as n8n workflow and import directly:
```json
{
  "name": "My Agent",
  "nodes": [...],
  "connections": {...},
  "metadata": {...}
}
```

### MindsDB Integration
Register knowledge base:
```bash
curl -X POST http://localhost:47334/api/v1/knowledge_bases \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_name": "My KB",
    "source": "fileSearchStores/xxx",
    "type": "gemini_file_search"
  }'
```

## 💰 Costs

| Operation | Cost |
|-----------|------|
| File Indexing | $0.15 per 1M tokens |
| Storage | FREE (indefinite) |
| Query Embeddings | FREE |
| Generated Tokens | $0.15-1.50 per 1M |

**Example**: 10,000 pages = ~$1.50 indexing cost, FREE queries

## 🛠️ Configuration

### Environment Variables
```bash
GEMINI_API_KEY=your-api-key
MINDSDB_HOST=http://localhost:47334
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600  # 100MB
```

### Model Configuration
```python
{
  "model": "gemini-2.5-flash",
  "temperature": 0.7,
  "top_k": 10,
  "max_output_tokens": 2048
}
```

### Chunking Configuration
```python
{
  "white_space_config": {
    "max_tokens_per_chunk": 200,
    "max_overlap_tokens": 20
  }
}
```

## 📝 Best Practices

### Document Preparation
✅ Use clear structure with headings  
✅ Include examples and use cases  
✅ Add table of contents  
✅ Use consistent formatting  
❌ Avoid scanned images without OCR  

### Instruction Writing
✅ Be specific about agent behavior  
✅ Include examples of expected responses  
✅ Specify error handling  
✅ Define tone and personality  
✅ Keep instructions under 5000 characters  

### Agent Configuration
✅ Start with temperature 0.7  
✅ Monitor token usage  
✅ Update documents monthly  
✅ Archive old versions  
✅ Test with sample queries  

## 🐛 Troubleshooting

### "Insufficient information" error
**Solution:**
1. Add more detailed sections (minimum 5)
2. Include examples and use cases
3. Ensure clear document structure

### "Upload timeout"
**Solution:**
1. Split large PDFs (>500MB)
2. Check file format compatibility
3. Verify network connectivity

### "MindsDB connection failed"
**Solution:**
1. Ensure MindsDB is running
2. Check MINDSDB_HOST environment variable
3. Agent still works without MindsDB

## 📚 Learning Resources

- [Gemini API Docs](https://ai.google.dev/docs)
- [Gemini File Search Guide](https://ai.google.dev/docs/file_search)
- [MindsDB Documentation](https://docs.mindsdb.com)
- [n8n Integration Guide](https://docs.n8n.io)

## 🧪 Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=backend tests/

# Specific test
pytest tests/test_agents.py -v
```

## 📖 API Documentation

Full API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Issues**: Create GitHub issue
- **Email**: support@example.com
- **Documentation**: Full docs at `/docs`

## 🎓 Example Workflow

```bash
# 1. Start server
python backend/main.py

# 2. Upload document
curl -X POST http://localhost:8000/api/v1/upload-and-process \
  -F "instructions=I need an agent that can help with customer support" \
  -F "file=@support_manual.pdf"

# 3. Get status
curl http://localhost:8000/api/v1/status/{task_id}

# 4. Export as n8n
curl http://localhost:8000/api/v1/export/{task_id}?format=n8n

# 5. Use in n8n workflow
# Import the exported JSON into n8n and deploy
```

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Maintainer**: Your Team