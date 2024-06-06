FROM python:3.11-slim

ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN bash setup.sh
RUN pip install --no-cache-dir -r requirements.txt
RUN bash .env
CMD exec bash run.sh