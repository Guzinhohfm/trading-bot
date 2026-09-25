FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "pydantic>=2.7" \
    "pydantic-settings>=2.3" \
    "pandas>=2.2" \
    "numpy>=1.26" \
    "pytest>=8.2"

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["pytest", "-q"]
