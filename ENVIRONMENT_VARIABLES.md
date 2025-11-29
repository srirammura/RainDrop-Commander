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
