FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
# Google Cloud プロジェクトのID
ENV PROJECT_ID <PROJECT_ID>
# Firestore の プロジェクトID
ENV FIRESTORE_PROJECT_ID <FIRESTORE_PROJECT_ID>
# 検索エンジンのロケーション
ENV VERTEX_AI_SEARCH_LOCATION global
# 検索エンジンのID
ENV VERTEX_AI_SEARCH_ENGINE_ID <SEARCH_ENGINE_ID>
# 絵文字のアイコンを有効にする
ENV FLET_WEB_USE_COLOR_EMOJI 1 

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN bash setup.sh
RUN pip install --no-cache-dir -r requirements.txt
CMD exec bash run.sh
