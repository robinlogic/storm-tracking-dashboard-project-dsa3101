FROM python:3.11-slim

WORKDIR /app
COPY . /app/frontend_ws

RUN pip install --upgrade pip
RUN pip install -r ./frontend_ws/docker/requirements.txt

WORKDIR /app/frontend_ws/app

EXPOSE 8050

CMD ["python3", "-u", "app.py"]
