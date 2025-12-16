FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .

RUN apt-get update && apt-get install -y build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -e .

COPY . /app

CMD ["python3", "-m", "app.main"]
