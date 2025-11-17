# ⚡ Quick Start Guide (5 minutes)

## Step 1: Get API Key (2 minutes)

1. Go to https://ai.google.dev/
2. Click "Create API Key"
3. Copy the key
4. Keep it safe! 🔐

## Step 2: Setup Project (1 minute)

```bash
# Clone or download the project
cd agent-builder-platform

# Create .env file
cp .env.example .env

# Edit .env and add your key:
# GEMINI_API_KEY=sk-your-key-here
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
# Then edit .env with your text editor
```

## Step 3: Install & Run (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

You should see:
```
============================================================
🚀 Agent Builder Platform Starting
============================================================
📁 Uploads: ./uploads
🔌 MindsDB: http://localhost:47334
📚 API Docs: http://localhost:8000/docs
============================================================
```

✅ **Server is running!**

## Step 4: Test It

Open in browser: http://localhost:8000/docs

You'll see the Swagger UI with all endpoints.

### Test with curl:

```bash
# Create a test file
echo "This is a test document about customer support procedures." > test.txt

# Upload it
curl -X POST http://localhost:8000/api/v1/upload-and-process \
  -F "instructions=Create an agent that helps with customer support" \
  -F "file=@test.txt"
```

You'll get:
```json
{
  "status": "processing_started",
  "task_id": "abc-123",
  "poll_url": "/api/v1/status/abc-123",
  "websocket_url": "ws://localhost:8000/ws/status/abc-123"
}
```

### Check status:

```bash
curl http://localhost:8000/api/v1/status/abc-123
```

### Export as JSON:

```bash
curl http://localhost:8000/api/v1/export/abc-123?format=json
```

## 🎯 What Just Happened?

1. ✅ You uploaded a document
2. ✅ Validated it with AI
3. ✅ Created a File Search Store
4. ✅ Generated an agent configuration
5. ✅ Ready to export to n8n or MindsDB!

## 🚀 Next Steps

### Option 1: Use the API
Check out http://localhost:8000/docs for full API reference

### Option 2: Build a Web UI
Use the React component from artifacts to create a nice interface

### Option 3: Integrate with n8n
Export your agent as JSON and import to n8n workflows

### Option 4: Use with MindsDB
Register knowledge bases for SQL-based queries

## 🆘 Troubleshooting

### "GEMINI_API_KEY not set"
```bash
# Make sure .env file exists and has:
GEMINI_API_KEY=your-key-here

# Or set it directly:
# Windows (PowerShell):
$env:GEMINI_API_KEY="your-key"

# Linux/Mac:
export GEMINI_API_KEY="your-key"
```

### "ModuleNotFoundError"
```bash
# Make sure all dependencies are installed
pip install -r requirements.txt

# Try upgrading pip
pip install --upgrade pip
```

### "Port 8000 already in use"
```bash
# Use different port:
python -c "import os; os.environ['PORT']='8001'; exec(open('main.py').read())"

# Or find and kill process using port 8000
# Windows: netstat -ano | findstr :8000
# Linux: lsof -i :8000
```

### "Connection refused"
- Make sure server is running
- Check if you're using correct URL (http://localhost:8000)
- Check firewall settings

## 📝 Example Usage

### Minimum viable example:

```python
import requests

# 1. Upload document
with open('my_document.pdf', 'rb') as f:
    files = {'file': f}
    data = {'instructions': 'Create a helpful assistant from this document'}
    
    response = requests.post(
        'http://localhost:8000/api/v1/upload-and-process',
        files=files,
        data=data
    )
    
    task_id = response.json()['task_id']
    print(f"Processing task: {task_id}")

# 2. Check status (poll or websocket)
import time
while True:
    status = requests.get(f'http://localhost:8000/api/v1/status/{task_id}')
    print(status.json()['current_step'])
    
    if status.json()['status'] == 'complete':
        break
    
    time.sleep(2)

# 3. Export agent
export = requests.post(f'http://localhost:8000/api/v1/export/{task_id}?format=json')
agent_config = export.json()

print("✅ Agent ready!")
print(agent_config)
```

## 🎓 Learn More

- **Full Docs**: README.md
- **API Docs**: http://localhost:8000/docs
- **Gemini API**: https://ai.google.dev/docs
- **n8n Integration**: https://docs.n8n.io

## 💡 Tips

- 🔄 Keep polling `/api/v1/status/{task_id}` or use WebSocket for real-time updates
- 📤 Maximum file size is 100MB
- 📝 Instructions should be at least 20 characters
- 🎯 More detailed instructions = better agent behavior
- 💾 Files are saved in `./uploads` directory

---

**Congratulations!** 🎉 You now have a working AI agent builder!

Next: Try uploading a real PDF document and see it in action.