FROM python:3.6-alpine
MAINTAINER Bhaa Shakur

ENV PYTHONUNBUFFERED 1

RUN mkdir /src
WORKDIR /src
COPY ./src /src

COPY ./requirements.txt /requirements.txt
RUN apk add --update --virtual .tmp-build-deps \
        gcc libc-dev linux-headers
RUN pip install -r /requirements.txt

RUN adduser -D user
USER user