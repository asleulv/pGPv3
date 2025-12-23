# Use a slim Python image
FROM python:3.11-slim

# Install system dependencies for MySQL
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory to /app
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything (including the 'pgp' folder) into /app
COPY . .

# Move into the nested directory where manage.py and core/ actually live
WORKDIR /app/pgp

# Now this command will find manage.py
RUN python manage.py collectstatic --noinput

# Start Gunicorn, pointing to the core.wsgi inside this nested folder
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]