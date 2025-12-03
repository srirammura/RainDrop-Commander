# Environment Variables for RainDrop Commander

## Required Environment Variables

### 1. `DJANGO_SECRET_KEY`
- **Description**: Django secret key used for cryptographic signing
- **Required**: Yes
- **Default**: `dev-secret-key-change-in-production` (development only)
- **How to generate**: 
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- **Example**: `django-insecure-abc123xyz789...` (50+ characters)
- **Used in**: `raindrop_commander/settings.py`

### 2. `ANTHROPIC_API_KEY`
- **Description**: Anthropic (Claude) API key for generating examples and rules using Claude models
- **Required**: Yes
- **Format**: Starts with `sk-ant-api03-`
- **Example**: `sk-ant-api03-your-anthropic-api-key-here`
- **Used in**: `commander/services/gemini_client.py` (Anthropic client)
- **Get it from**: https://console.anthropic.com/settings/keys

## Optional Environment Variables

### 3. `DEBUG`
- **Description**: Enable/disable Django debug mode
- **Required**: No
- **Default**: `False`
- **Values**: `True` or `False` (as string)
- **Production**: Must be `False`
- **Development**: Can be `True` for detailed error pages
- **Used in**: `raindrop_commander/settings.py`

### 4. `ALLOWED_HOSTS`
- **Description**: Comma-separated list of allowed hostnames for the Django app
- **Required**: No (defaults to `*` which allows all hosts)
- **Default**: `*` (allows all hosts)
- **Production Example**: `raindrop-commander.onrender.com,your-custom-domain.com`
- **Development**: Can be `*` or `localhost,127.0.0.1`
- **Used in**: `raindrop_commander/settings.py`

### 5. `CLAUDE_EFFORT_ENABLED`
- **Description**: Enable/disable Claude Opus 4.5 effort parameter feature for cost optimization
- **Required**: No
- **Default**: `true`
- **Values**: `true` or `false` (as string)
- **Purpose**: When enabled, uses effort parameter to reduce token usage by 50-80% on simple tasks
- **Used in**: `commander/services/effort_config.py`

### 6. `CLAUDE_EFFORT_DEFAULT`
- **Description**: Default effort level when task type is unknown
- **Required**: No
- **Default**: `medium`
- **Values**: `low`, `medium`, or `high`
- **Purpose**: Fallback effort level for unclassified tasks
- **Used in**: `commander/services/effort_config.py`

### 7. `CACHE_ENABLED`
- **Description**: Enable/disable prompt caching (exact and semantic)
- **Required**: No
- **Default**: `true`
- **Values**: `true` or `false` (as string)
- **Purpose**: When enabled, caches LLM responses to reduce token usage and improve response times
- **Used in**: `commander/services/cache_service.py`

### 8. `REDIS_URL`
- **Description**: Redis connection URL for distributed caching
- **Required**: No (falls back to in-memory cache if not provided)
- **Default**: `redis://localhost:6379/0`
- **Values**: Valid Redis URL (e.g., `redis://localhost:6379/0`, `rediss://user:pass@host:6380/0`)
- **Purpose**: Enables distributed caching across multiple instances
- **TLS Support**: Use `rediss://` (with double 's') for TLS connections (e.g., Upstash)
- **Example (Upstash)**: `rediss://default:password@host.upstash.io:6379`
- **Used in**: `commander/services/cache_service.py`

### 9. `OPENAI_API_KEY`
- **Description**: OpenAI API key for generating embeddings for semantic caching
- **Required**: No (semantic caching disabled if not provided)
- **Default**: None
- **Values**: Valid OpenAI API key
- **Purpose**: Used to generate embeddings for semantic similarity matching
- **Used in**: `commander/services/embedding_service.py`

### 10. `EMBEDDING_MODEL`
- **Description**: OpenAI embedding model to use for semantic caching
- **Required**: No
- **Default**: `text-embedding-3-small`
- **Values**: Valid OpenAI embedding model name
- **Purpose**: Determines which embedding model to use for semantic similarity
- **Used in**: `commander/services/embedding_service.py`

### 11. `SEMANTIC_CACHE_THRESHOLD`
- **Description**: Minimum similarity score (0.0-1.0) for semantic cache hits
- **Required**: No
- **Default**: `0.85`
- **Values**: Float between 0.0 and 1.0
- **Purpose**: Higher values (0.9+) require very similar prompts, lower values (0.7) allow more flexible matching
- **Used in**: `commander/services/cache_service.py`

### 12. `CACHE_TTL_EXAMPLES`
- **Description**: Time-to-live for example generation cache entries (in seconds)
- **Required**: No
- **Default**: `604800` (7 days)
- **Values**: Positive integer (seconds)
- **Purpose**: How long to cache example generation results
- **Used in**: `commander/services/cache_service.py`

### 13. `CACHE_TTL_EVALUATION`
- **Description**: Time-to-live for evaluation cache entries (in seconds)
- **Required**: No
- **Default**: `86400` (24 hours)
- **Values**: Positive integer (seconds)
- **Purpose**: How long to cache rule potential evaluation results
- **Used in**: `commander/services/cache_service.py`

### 14. `CACHE_TTL_DEFAULT`
- **Description**: Default time-to-live for cache entries (in seconds)
- **Required**: No
- **Default**: `86400` (24 hours)
- **Values**: Positive integer (seconds)
- **Purpose**: Default TTL for cache entries that don't match specific task types
- **Used in**: `commander/services/cache_service.py`

## Complete Environment Variables List

### For Local Development (.env file):
```env
DJANGO_SECRET_KEY=your-secret-key-here
ANTHROPIC_API_KEY=sk-ant-api03-your-anthropic-api-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### For Production (Render):
```env
DJANGO_SECRET_KEY=your-generated-secret-key-50-chars-minimum
ANTHROPIC_API_KEY=sk-ant-api03-your-anthropic-api-key-here
DEBUG=False
ALLOWED_HOSTS=raindrop-commander.onrender.com
CLAUDE_EFFORT_ENABLED=true
CLAUDE_EFFORT_DEFAULT=medium
CACHE_ENABLED=true
REDIS_URL=rediss://default:password@host.upstash.io:6379
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
SEMANTIC_CACHE_THRESHOLD=0.85
CACHE_TTL_EXAMPLES=604800
CACHE_TTL_EVALUATION=86400
```

## Setting Environment Variables

### Local Development:
Create a `.env` file in the project root:
```bash
cd "/Users/srirammuralidharan/AI Projects/raindrop-Commander"
cat > .env << EOF
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
ANTHROPIC_API_KEY=your-anthropic-api-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EOF
```

### Render Dashboard:
1. Go to your service → **Environment**
2. Click **"Add Environment Variable"**
3. Add each variable:
   - **Key**: `DJANGO_SECRET_KEY`
   - **Value**: (paste generated secret key)
   - **Apply to**: ☑ Production ☑ Preview
4. Repeat for all variables

## Notes

- **Never commit `.env` file** to git (already in `.gitignore`)
- **DJANGO_SECRET_KEY** should be unique and secret for each environment
- **ANTHROPIC_API_KEY** is required for the app to function (LLM calls)
- **DEBUG=False** in production for security
- **ALLOWED_HOSTS** should match your deployment URL in production
