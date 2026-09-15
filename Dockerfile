FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY agents ./agents
COPY frontend ./frontend
RUN mkdir -p /app/.local && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "agents.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
