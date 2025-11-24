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

## Deployment on Render

1. Push your code to GitHub

2. In Render dashboard:
   - Create a new Web Service
   - Connect your GitHub repository
   - Use these settings:
     - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
     - **Start Command**: `gunicorn raindrop_commander.wsgi:application`
     - **Environment**: Python 3

3. Set environment variables in Render:
   - `DJANGO_SECRET_KEY`: Generate a secure secret key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `DEBUG`: Set to `False` for production
   - `ALLOWED_HOSTS`: Your Render service URL (e.g., `raindrop-commander.onrender.com`)

4. Deploy!

## Environment Variables

- `DJANGO_SECRET_KEY`: Django secret key (required)
- `OPENAI_API_KEY`: OpenAI API key (required)
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
