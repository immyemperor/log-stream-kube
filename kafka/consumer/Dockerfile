FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5003
# CMD ["python", "app.py"]

CMD ["gunicorn", \
    "--bind", "0.0.0.0:5003", \
    "--workers", "2", \
    "--threads", "1", \
    "--timeout", "120", \
    "consumer:app"]

