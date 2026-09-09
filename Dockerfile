FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY karuvi/ ./karuvi/

RUN uv pip install --system --no-cache .

EXPOSE 8000

ENTRYPOINT ["karuvi"]
CMD ["--help"]
