FROM python:3.11-slim

WORKDIR /app

COPY src/pybot/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/pybot .

CMD ["python", "pybot/chatbot.py"]
