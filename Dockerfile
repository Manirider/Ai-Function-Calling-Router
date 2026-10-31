FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m -u 1000 appuser
COPY src ./src
COPY data ./data
COPY evaluate_router.py .
ENV PROVIDER_MODE=offline
ENV OUTPUT_DIR=output
RUN mkdir -p output && chown -R appuser:appuser /app && chmod 777 output
USER appuser
CMD ["python", "evaluate_router.py"]
