FROM python:3.11-slim

WORKDIR /project

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Build the vector index at build time
RUN python setup.py

# Expose port
EXPOSE 10000

# Start server
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"
