FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

EXPOSE 8083

CMD ["python", "-m", "uvicorn", "sandbox_agent.main:app", "--host", "0.0.0.0", "--port", "8083"]
