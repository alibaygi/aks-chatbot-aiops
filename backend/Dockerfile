FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Install Python dependencies
# Build context is the project root, so pyproject.toml is at .
COPY pyproject.toml .
RUN uv pip install --system -e .

# Copy application code (backend/ is a directory; use trailing slash to include
# all files AND subdirectories — e.g. app/, which contains the Python package)
COPY backend/ /app/backend/
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
