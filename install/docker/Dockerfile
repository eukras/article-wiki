FROM python:3.11-slim

WORKDIR /app

COPY ./wiki /app/wiki

RUN pip install -r wiki/requirements.txt

WORKDIR /app/wiki

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
