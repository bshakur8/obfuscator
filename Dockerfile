FROM python:3.6-alpine
MAINTAINER Bhaa Shakur

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "/app/:${PYTHONPATH}"


RUN mkdir /app
RUN mkdir /app/src
RUN mkdir /app/tests
COPY ./src /app/src
COPY ./tests /app/tests
WORKDIR /src

COPY ./requirements.txt /app/requirements.txt
RUN apk add --update --no-cache --virtual .tmp-build-deps \
        gcc libc-dev linux-headers
RUN pip install -r /app/requirements.txt

RUN adduser -D user
USER user