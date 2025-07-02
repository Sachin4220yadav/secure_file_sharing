FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements-legacy.txt .
RUN pip install --no-cache-dir -r requirements-legacy.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "app.py"]