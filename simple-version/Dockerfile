FROM python:3.12-slim

ENV PYTHONUNBUFFERED=True
# Google Cloud プロジェクトのID

ENV APP_HOME=/app
WORKDIR $APP_HOME
COPY . ./

RUN pip install --no-cache-dir -r requirements.txt
CMD exec bash run.sh
