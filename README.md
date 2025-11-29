# RainDrop DeepSearch Commander

AI supervisor suite for auditing and improving classification rules in RainDrop's DeepSearch feature.

## Features

- **Red Team Tool**: Tests rule robustness against edge cases
- **Overfit Detector**: Measures example diversity and variance
- **Semantic Mapper**: Generates boundary examples for rule refinement

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file:
```
DJANGO_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
DEBUG=True
ALLOWED_HOSTS=localhost
```

3. Run migrations (if needed):
```bash
python manage.py migrate
```

4. Collect static files:
```bash
python manage.py collectstatic --noinput
```

5. Run the development server:
```bash
python manage.py runserver
```

## Deployment on Render (Docker)

The application is dockerized for consistent deployment across environments.

### Using Docker on Render:

1. Push your code to GitHub

2. In Render dashboard:
   - Create a new **Web Service**
   - Select **"Docker"** as the environment (not Python)
   - Connect your GitHub repository
   - Render will automatically detect the `Dockerfile`

3. Set environment variables in Render:
   - `DJANGO_SECRET_KEY`: Generate using `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - `ANTHROPIC_API_KEY`: Your Anthropic (Claude) API key
   - `CLAUDE_EFFORT_ENABLED`: Enable effort parameter for cost optimization (default: `true`)
   - `CLAUDE_EFFORT_DEFAULT`: Default effort level for unknown tasks (default: `medium`)
   - `DEBUG`: Set to `False` for production
   - `ALLOWED_HOSTS`: Your Render service URL (e.g., `raindrop-commander.onrender.com`)
   - `PORT`: Set to `8000` (or let Render auto-assign)

4. Deploy!

### Local Docker Testing:

```bash
# Build the image
docker build -t raindrop-commander .

# Run the container
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=your-secret-key \
  -e ANTHROPIC_API_KEY=your-api-key \
  -e DEBUG=False \
  -e ALLOWED_HOSTS=localhost \
  raindrop-commander
```

### Alternative: Non-Docker Deployment

If you prefer the original Python deployment method, you can still use:
- **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command**: `gunicorn raindrop_commander.wsgi:application --bind 0.0.0.0:$PORT`
- **Environment**: Python 3.9

## Environment Variables

- `DJANGO_SECRET_KEY`: Django secret key (required)
- `ANTHROPIC_API_KEY`: Anthropic (Claude) API key (required)
- `CLAUDE_EFFORT_ENABLED`: Enable effort parameter for cost optimization (optional, default: `true`)
- `CLAUDE_EFFORT_DEFAULT`: Default effort level for unknown tasks (optional, default: `medium`)
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
