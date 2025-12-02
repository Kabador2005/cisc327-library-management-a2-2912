# Use Python 3.12 as base image
FROM python:3.12-slim

# Set working directory in container
WORKDIR /app

# Install Flask and other dependencies directly
RUN pip install --no-cache-dir Flask==3.0.0 Werkzeug==3.0.1 requests

# Copy all source files to container
COPY . .

# Expose port 5000
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Run the Flask application
CMD ["python", "app.py"]