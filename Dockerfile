FROM python:3.11-slim

WORKDIR /app/pybot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/pybot .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
