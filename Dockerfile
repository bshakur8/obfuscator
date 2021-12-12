FROM python:3.6-alpine
MAINTAINER Bhaa Shakur

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app/"


WORKDIR /usr/src/app
COPY . .

RUN apk add --update --no-cache --virtual .tmp-build-deps \
        gcc libc-dev linux-headers

RUN pip install -r ./requirements.txt

RUN chmod +x ./obfuscator/main.py
ENTRYPOINT ["./obfuscator/main.py"]