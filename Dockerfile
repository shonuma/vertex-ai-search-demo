FROM python:3.12-slim

ENV PYTHONUNBUFFERED=True
# Google Cloud プロジェクトのID
ENV PROJECT_ID=<change_it>
# Firestore の プロジェクトID
ENV FIRESTORE_PROJECT_ID=<change_it>
# 検索エンジンのロケーション
ENV VERTEX_AI_SEARCH_LOCATION=global
# 検索エンジンのID
ENV VERTEX_AI_SEARCH_ENGINE_ID=<change_it>
# 絵文字のアイコンを有効にする
ENV FLET_WEB_USE_COLOR_EMOJI=1
# FAQ の URL
ENV FAQ_URL=https://www.google.com/
# このアカウントの権限でドライブのデータを取得します
ENV SUBJECT=<change_it>
# サーバーのサービスアカウントの情報
ENV SERVICE_ACCOUNT_INFO=<change_it>

ENV APP_HOME=/app
WORKDIR $APP_HOME
COPY . ./

RUN bash setup.sh
RUN pip install --no-cache-dir -r requirements.txt
CMD exec bash run.sh
