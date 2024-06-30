FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
# Google Cloud プロジェクトのID
ENV PROJECT_ID <PROJECT_ID>
# 検索エンジンのロケーション
ENV VERTEX_AI_SEARCH_LOCATION global
# 検索エンジンのID
ENV VERTEX_AI_SEARCH_ENGINE_ID <SEARCH_ENGINE_ID>

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN bash setup.sh
RUN pip install --no-cache-dir -r requirements.txt
CMD exec bash run.sh
