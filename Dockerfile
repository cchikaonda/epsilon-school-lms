# Use Python 3.12 because Django requires Python 3.12+
FROM python:3.12-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Send Python output directly to the terminal
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install PostgreSQL/build dependencies AND Node.js (required for Tailwind CSS v4)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    pkg-config \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first for caching npm dependencies
COPY package.json package-lock.json* ./

# Install Node dependencies (Tailwind CLI)
RUN npm install

# Copy Python requirements first for Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Django project (including src/input.css)
COPY . .

# Compile Tailwind CSS for production/container use
RUN npx @tailwindcss/cli -i ./src/input.css -o ./static/css/tailwind.css

# Collect static files inside the container
RUN python manage.py collectstatic --noinput

# Django port
EXPOSE 8000

# Start Django (For production use Gunicorn, or keep runserver for local dev container)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]