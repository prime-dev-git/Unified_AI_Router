# Unified AI Router  
## Comprehensive Technical Documentation  

---
### 1. Overview  

The Unified AI Router is a production-ready FastAPI service that provides a single, consistent interface for interacting with multiple AI providers—including cloud-based services (OpenAI, Anthropic, Google Gemini) and local inference engines (Ollama). This architecture enables seamless provider switching without modifying client applications, supports privacy-sensitive workflows via local inference, and simplifies integration testing across AI platforms.

**Key Capabilities**  
- Single endpoint (`/ai/chat`) routes requests to any configured provider  
- Normalized request/response schema across all providers  
- Local inference via Ollama with zero external dependencies  
- Production-grade error handling and input validation  
- Environment-driven configuration with secrets management  
- CORS protection and structured logging  

---

### 2. System Requirements  

#### Hardware  
| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| CPU | 4 cores | 8+ cores | Required for Ollama inference |
| RAM | 8 GB | 16+ GB | 8 GB supports 3B-parameter models; 16+ GB required for 7B+ models |
| GPU | None | NVIDIA with 8+ GB VRAM | Accelerates Ollama inference; not required for cloud providers |
| Storage | 5 GB free | 20+ GB free | Model storage for Ollama (varies by model size) |

#### Software  
- Python 3.10 or higher  
- pip package manager  
- Ollama 0.1.34 or higher (required only for local inference)  
- Supported operating systems: Linux, macOS 12+, Windows 10+  

---

### 3. Installation and Setup  

#### 3.1. Project Initialization  
```bash
# Create dedicated directory for the service
mkdir /opt/ai-router && cd /opt/ai-router

# Create isolated Python environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

#### 3.2. Environment Configuration  
Create `.env` file from template:  
```bash
cp .env.example .env
```

Edit `.env` with required values:  
```ini
# Cloud provider API keys (required for cloud services)
OPENAI_API_KEY=sk-proj_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyC_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Ollama configuration (optional; enables local inference)
OLLAMA_HOST=http://localhost:11434
DEFAULT_OLLAMA_MODEL=llama3.2:3b

# Default models for cloud providers
DEFAULT_OPENAI_MODEL=gpt-4o-mini
DEFAULT_ANTHROPIC_MODEL=claude-3-5-haiku-20241022
DEFAULT_GEMINI_MODEL=gemini-1.5-flash

# Security configuration
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.example.com
```

> **Critical Security Note**: Never commit `.env` to version control. Add to `.gitignore` or equivalent exclusion mechanism.

#### 3.3. Ollama Setup (Local Inference)  
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service (Linux/macOS)
systemctl --user start ollama   # Persistent systemd service
# OR for temporary session:
ollama serve &

# Pull required models before first use
ollama pull llama3.2:3b         # Recommended starting model (3.2B parameters)
ollama pull qwen2.5:7b          # Alternative for multilingual tasks
```

> **Windows Note**: Install Ollama via official installer (https://ollama.com/download). Service starts automatically after installation.

#### 3.4. Service Startup  
```bash
# Development mode (auto-reload enabled)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode (disable reload)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Verify service health:  
```bash
curl http://localhost:8000/health
```

Expected response:  
```json
{
  "status": "healthy",
  "providers": {
    "openai": true,
    "anthropic": true,
    "gemini": true,
    "ollama": true
  },
  "ollama_host": "http://localhost:11434"
}
```

---

### 4. API Specification  

#### 4.1. Unified Endpoint  
`POST /ai/chat`  

**Request Schema**  
| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `provider` | string | Yes | — | `openai`, `anthropic`, `gemini`, `ollama` | Target AI provider |
| `prompt` | string | Yes | — | 1–10,000 characters | User input text |
| `model` | string | No | Provider default | Provider-specific | Explicit model selection |
| `max_tokens` | integer | No | 500 | 1–4096 | Maximum response length |
| `temperature` | float | No | 0.7 | 0.0–2.0 | Response randomness control |

**Example Request**  
```json
{
  "provider": "ollama",
  "prompt": "Explain quantum entanglement in simple terms",
  "model": "llama3.2:3b",
  "max_tokens": 300,
  "temperature": 0.3
}
```

**Success Response (HTTP 200)**  
```json
{
  "provider": "ollama",
  "model": "llama3.2:3b",
  "response": "Quantum entanglement is a phenomenon where...",
  "prompt_tokens": null,
  "completion_tokens": null
}
```

**Error Responses**  
| HTTP Code | Condition | Example Message |
|-----------|-----------|-----------------|
| 400 | Invalid provider/model | `Unsupported provider: 'cohere'. Available: ['openai','anthropic','gemini','ollama']` |
| 400 | Missing required field | `prompt: Field required` |
| 401 | Invalid API key | `OpenAI API Error: Incorrect API key provided` |
| 400 | Ollama model not pulled | `Ollama model 'mistral:7b' not found. Run: ollama pull mistral:7b` |
| 503 | Ollama server unreachable | `Ollama server not running at http://localhost:11434` |
| 502 | Provider timeout/error | `Gemini request failed: Timeout` |

#### 4.2. Health Endpoint  
`GET /health`  

Returns service status and provider availability. Use for load balancer health checks.

---

### 5. Provider Configuration Reference  

#### 5.1. Cloud Providers  
| Provider | API Key Source | Default Model | Notes |
|----------|----------------|---------------|-------|
| OpenAI | https://platform.openai.com/api-keys | `gpt-4o-mini` | Most cost-effective GPT model |
| Anthropic | https://console.anthropic.com/settings/keys | `claude-3-5-haiku-20241022` | Fastest Claude model |
| Google Gemini | https://aistudio.google.com/app/apikey | `gemini-1.5-flash` | Optimized for high-volume tasks |

#### 5.2. Ollama (Local Inference)  
| Configuration | Default Value | Description |
|---------------|---------------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address (must be reachable from router) |
| `DEFAULT_OLLAMA_MODEL` | `llama3.2:3b` | Model used when none specified in request |
| Model storage path | `~/.ollama/models` | Persistent storage location for downloaded models |

**Recommended Ollama Models**  
| Model | Parameters | RAM Required | Use Case |
|-------|------------|--------------|----------|
| `llama3.2:1b` | 1B | ~2 GB | Low-resource environments |
| `llama3.2:3b` | 3B | ~4 GB | General purpose (recommended default) |
| `qwen2.5:7b` | 7B | ~8 GB | Multilingual applications |
| `llama3.1:8b` | 8B | ~10 GB | Higher quality output |

> **Model Management**:  
> ```bash
> ollama list          # View downloaded models
> ollama pull <model>  # Download new model
> ollama rm <model>    # Remove unused model
> ```

---

### 6. Security Configuration  

#### 6.1. Critical Protections  
- **Secrets isolation**: API keys loaded exclusively from environment variables  
- **CORS enforcement**: Restricts frontend origins via `ALLOWED_ORIGINS`  
- **Input validation**: Prevents oversized prompts and invalid parameters  
- **Error sanitization**: Production errors never expose stack traces or secrets  

#### 6.2. Production Hardening Checklist  
- [ ] Disable `--reload` flag in production deployments  
- [ ] Restrict `ALLOWED_ORIGINS` to authorized frontend domains only  
- [ ] Deploy behind reverse proxy (Nginx/Traefik) with TLS termination  
- [ ] Implement API key authentication for the router itself  
- [ ] Store secrets in vault (HashiCorp Vault, AWS Secrets Manager) instead of `.env`  
- [ ] Add rate limiting middleware (e.g., `slowapi`)  
- [ ] Enable structured JSON logging to SIEM system  
- [ ] Isolate Ollama service to localhost-only network interface  

> **Ollama Security Warning**: Ollama has no built-in authentication. Never expose port 11434 directly to untrusted networks. Always route through this service which can implement authentication layers.

---

### 7. Troubleshooting Guide  

#### 7.1. Common Issues and Resolutions  

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `503 Service Unavailable` for Ollama | Ollama service not running | Start service: `systemctl --user start ollama` |
| `400 model not found` | Model not pulled locally | Run: `ollama pull <model-name>` |
| `401 Unauthorized` | Invalid API key | Verify key format and permissions in provider dashboard |
| `502 Bad Gateway` | Provider timeout | Increase timeout in `ai_provider.py` or check network connectivity |
| CORS errors in browser | Origin mismatch | Update `ALLOWED_ORIGINS` to match frontend URL exactly |
| Slow Ollama responses | Insufficient RAM/GPU | Use smaller model (`llama3.2:1b`) or add swap space |

#### 7.2. Diagnostic Commands  
```bash
# Verify Ollama service status
systemctl --user status ollama

# Test Ollama directly (bypass router)
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "test",
  "stream": false
}'

# Check router logs
tail -f /opt/ai-router/logs/app.log

# Validate environment variables loaded
grep -v "^#" .env | xargs -I {} echo "Checking: {}" | while read line; do 
  key=$(echo $line | cut -d= -f1); 
  echo "$key=${!key:-(NOT SET)}"; 
done
```

---

### 8. Production Deployment  

#### 8.1. Systemd Service Configuration  
Create `/etc/systemd/system/ai-router.service`:  
```ini
[Unit]
Description=Unified AI Router Service
After=network.target

[Service]
Type=exec
User=ai-router
WorkingDirectory=/opt/ai-router
EnvironmentFile=/opt/ai-router/.env
ExecStart=/opt/ai-router/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start service:  
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-router
sudo systemctl start ai-router
```

#### 8.2. Reverse Proxy Configuration (Nginx)  
```nginx
server {
    listen 443 ssl;
    server_name ai-router.example.com;

    ssl_certificate /etc/letsencrypt/live/ai-router.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai-router.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings for long-running inference
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

#### 8.3. Monitoring Recommendations  
- **Health checks**: Poll `/health` endpoint every 30 seconds  
- **Log aggregation**: Ship logs to ELK stack or Splunk  
- **Metrics**: Track requests per provider, error rates, response latency  
- **Cost monitoring**: Log token usage for cloud providers to track expenses  

---

### 9. Extending the Router  

#### 9.1. Adding New Providers  
1. Add API key variable to `config.py` `Settings` class  
2. Implement provider function in `ai_provider.py` following existing patterns  
3. Register function in `PROVIDER_MAP` dictionary  
4. Update `.env.example` with new configuration variables  
5. Add provider to health check endpoint  

#### 9.2. Custom Routing Logic  
Modify `main.py` to implement business logic such as:  
- Automatic provider selection based on prompt content  
- Fallback chains (e.g., try Ollama → OpenAI → Anthropic)  
- Cost-aware routing (prefer cheaper models for simple tasks)  
- Privacy-aware routing (route sensitive prompts to Ollama)  

Example privacy routing snippet:  
```python
SENSITIVE_KEYWORDS = ["password", "ssn", "credit card", "confidential"]

if any(kw in request.prompt.lower() for kw in SENSITIVE_KEYWORDS):
    request.provider = "ollama"  # Force local processing for sensitive data
```

---

### 10. Support and Maintenance  

#### 10.1. Update Procedure  
```bash
# Stop service
sudo systemctl stop ai-router

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Pull latest code changes
git pull origin main  # Or your deployment method

# Restart service
sudo systemctl start ai-router
```

#### 10.2. Provider API Changes  
Monitor provider changelogs for breaking changes:  
- OpenAI: https://platform.openai.com/docs/changelog  
- Anthropic: https://docs.anthropic.com/claude/changelog  
- Google AI: https://ai.google.dev/gemini-api/updates  
- Ollama: https://github.com/ollama/ollama/releases  

When provider APIs change:  
1. Update corresponding function in `ai_provider.py`  
2. Test with provider's sandbox environment  
3. Deploy during maintenance window with rollback plan  

---

### Appendix A: Complete curl Test Suite  

```bash
# Health check
curl http://localhost:8000/health

# Ollama (local inference)
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","prompt":"What is photosynthesis?","max_tokens":200}'

# OpenAI
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","prompt":"Explain neural networks","temperature":0.5}'

# Anthropic
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"anthropic","prompt":"Write a SQL query for user analytics","model":"claude-3-5-haiku-20241022"}'

# Gemini
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","prompt":"Compare renewable energy sources","max_tokens":400}'

# Error case: unsupported provider
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"cohere","prompt":"test"}'

# Error case: missing prompt
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama"}'
```

---

*Document Version: 2.1*  
*Last Updated: February 2026*  