FROM python:3.11-slim

# Disable output buffering so logs are visible immediately
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Copy dependency list first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Run the application
CMD ["python", "main.py"]

