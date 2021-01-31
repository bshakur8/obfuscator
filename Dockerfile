FROM python:3.6-alpine
MAINTAINER Bhaa Shakur

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "/obfuscator/:${PYTHONPATH}"


RUN mkdir /obfuscator

COPY ./ /obfuscator/
WORKDIR /obfuscator

COPY ./requirements.txt /obfuscator/requirements.txt
RUN apk add --update --no-cache --virtual .tmp-build-deps \
        gcc libc-dev linux-headers

RUN pip install -r /obfuscator/requirements.txt

RUN adduser -D dockuser && chown -R dockuser /obfuscator
USER dockuser
