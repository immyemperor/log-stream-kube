FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
COPY . .
ENV FLASK_APP=app:create_app
ENTRYPOINT ["./entrypoint.sh"]
EXPOSE 5003
# CMD ["python", "app.py"]

CMD ["gunicorn", \
    "--bind", "0.0.0.0:5003", \
    "--workers", "2", \
    "--threads", "1", \
    "--timeout", "120", \
    "app:create_app()"]

