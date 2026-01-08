FROM python:3.10-slim
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/backend_ws/secrets/vigilant-cider-474204-j7-98a4813d5eaa.json

WORKDIR /app
COPY backend_ws ./backend_ws

RUN pip install -r ./backend_ws/requirements.txt

EXPOSE 8000

CMD ["python", "-m", "backend_ws.app.app"]
