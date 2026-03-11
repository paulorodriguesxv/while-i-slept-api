FROM python:3.12-slim

RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY scripts ./scripts
COPY docs ./docs
COPY openapi.yaml ./

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "while_i_slept_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
