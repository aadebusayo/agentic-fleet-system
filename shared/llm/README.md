# LLM Layer Configuration

The platform uses a provider-agnostic LLM configuration model with routing by intent/profile.

## Configuration Dimensions

- provider (`openai-compatible`, `azure-openai`, `anthropic`, `gemini`, `local-endpoint`, `stub`)
- model (e.g., `gpt-4o-mini`, `llama3.1-70b-instruct`)
- temperature
- max tokens
- timeout
- policy tags (`safe`, `high-precision`, `cost-optimized`)

## Runtime Behavior

- Backend chooses an `llmProfile` from intent.
- Sandbox runtime resolves provider/model settings for that profile.
- Control-plane policy can allow/deny model profile usage before execution.
- When `AGENT_LLM_FAILOVER_ENABLED=true`, sandbox runtime tries providers in `AGENT_LLM_FAILOVER_CHAIN` order and returns the first successful response.

## Environment Variables

- `AGENT_LLM_PROVIDER` default: `openai-compatible`
- `AGENT_LLM_FAILOVER_ENABLED` default: `true`
- `AGENT_LLM_FAILOVER_CHAIN` default: `openai-compatible,azure-openai,anthropic,gemini,local-endpoint`
- `AGENT_LLM_MODEL` default: `gpt-4o-mini`
- `AGENT_LLM_TEMPERATURE` default: `0.2`
- `AGENT_LLM_MAX_TOKENS` default: `512`
- `AGENT_LLM_TIMEOUT_SECONDS` default: `30`
- `AGENT_LLM_ENDPOINT` required for `openai-compatible`
- `AGENT_LLM_API_KEY` required for `openai-compatible`

### Online-first failover (recommended)

- Keep `AGENT_LLM_FAILOVER_ENABLED=true`.
- Set `AGENT_LLM_FAILOVER_CHAIN` so all online providers come before `local-endpoint`.
- Example: `AGENT_LLM_FAILOVER_CHAIN=openai-compatible,azure-openai,anthropic,gemini,local-endpoint`.
- Set `AGENT_LLM_FAILOVER_ENABLED=false` only if you want strict single-provider behavior from `AGENT_LLM_PROVIDER`.

### Azure OpenAI

- `AGENT_LLM_PROVIDER=azure-openai`
- `AGENT_AZURE_OPENAI_ENDPOINT` preferred (`https://<resource>.openai.azure.com`)
- `AGENT_AZURE_OPENAI_API_KEY` preferred
- `AGENT_AZURE_OPENAI_DEPLOYMENT` required
- `AGENT_AZURE_OPENAI_API_VERSION` optional (default `2024-06-01`)
- Fallbacks still supported: `AGENT_LLM_ENDPOINT` and `AGENT_LLM_API_KEY`

### Anthropic

- `AGENT_LLM_PROVIDER=anthropic`
- `AGENT_ANTHROPIC_API_KEY` required (or fallback `AGENT_LLM_API_KEY`)
- `AGENT_ANTHROPIC_ENDPOINT` optional (default `https://api.anthropic.com/v1/messages`)
- `AGENT_ANTHROPIC_VERSION` optional (default `2023-06-01`)

### Gemini

- `AGENT_LLM_PROVIDER=gemini`
- `AGENT_GEMINI_API_KEY` required (or fallback `AGENT_LLM_API_KEY`)
- `AGENT_GEMINI_ENDPOINT` optional custom URL template

### Local Endpoint (self-hosted/local model)

- `AGENT_LLM_PROVIDER=local-endpoint`
- `AGENT_LOCAL_LLM_ENDPOINT` required (or fallback `AGENT_LLM_ENDPOINT`)
- `AGENT_LOCAL_LLM_FORMAT` optional, default `openai-compatible` (`openai-compatible` or `ollama`)
- `AGENT_LOCAL_LLM_API_KEY` optional (used for bearer auth with local gateways)

Example local setups:

- OpenAI-compatible local gateway: set endpoint to your `/v1/chat/completions` URL and format `openai-compatible`.
- Ollama local runtime: set endpoint to `http://localhost:11434/api/chat` and format `ollama`.

### Stub (dev/test only)

- `AGENT_LLM_PROVIDER=stub`
- `AGENT_ALLOW_STUB_LLM=true` required

See `llm-routing.example.json` for a full routing contract.
