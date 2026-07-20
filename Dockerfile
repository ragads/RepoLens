# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environmental variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (build-essential for any wheel that needs
# compiling, curl for the HEALTHCHECK below). No Node.js — nothing in this
# repo is TypeScript/JS.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the working directory
COPY . .

EXPOSE 8505

# Healthcheck (uses $PORT when the host provides one, e.g. Render).
HEALTHCHECK CMD curl --fail http://localhost:${PORT:-8505}/_stcore/health || exit 1

# Bind to the host-provided $PORT (Render sets this dynamically); default 8505 locally.
# Shell form so ${PORT} is expanded at runtime.
CMD streamlit run app.py --server.port ${PORT:-8505} --server.address 0.0.0.0
