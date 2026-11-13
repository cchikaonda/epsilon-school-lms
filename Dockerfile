# Use Python 3.12 because Django requires Python 3.12+
FROM python:3.12-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Send Python output directly to the terminal
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install PostgreSQL build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements first for Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Django project (including your pre-compiled static/css/tailwind.css)
COPY . .

# Collect static files inside the container
RUN python manage.py collectstatic --noinput

# Django port
EXPOSE 8000

# Start Django (runs migrations automatically on startup, then runs server)
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]