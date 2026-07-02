# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy the rest of the application code
COPY . /app/

# Collect static files during build phase using a dummy SECRET_KEY
RUN SECRET_KEY=dummy_key_for_collectstatic python manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Run database migrations and start gunicorn server
CMD python manage.py migrate && gunicorn core.wsgi:application --bind 0.0.0.0:8000
