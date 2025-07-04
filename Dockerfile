# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app files
COPY . .

# Expose the port Fly expects
EXPOSE 8080

# Tell gunicorn to listen on 0.0.0.0:8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
