GREEN="\033[32m"
RESET="\033[00m"

temp_docker=$(mktemp Dockerfile.XXXXXX)
trap "rm -rf $temp_docker" EXIT INT

echo "${GREEN}============= Building Obfuscator =============${RESET}"
echo "${GREEN}===============================================${RESET}"

cat > $temp_docker <<EOF1
FROM python:3.11-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "${PYTHONPATH}:/app"

RUN apk add --update --virtual .tmp-build-deps gcc g++ libc-dev linux-headers
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

WORKDIR /app
COPY . /app
RUN pip install -r /app/requirements.txt

RUN chmod +x ./obfuscator/main.py
ENTRYPOINT ["./obfuscator/main.py"]
EOF1

docker build -f $temp_docker . -t obfuscator || exit
rm -rf $temp_docker

echo "${GREEN}======================= Image Built ========================${RESET}"
echo "${GREEN}INFO${RESET}: Running Obfuscator. For help, run with --help"
echo "${GREEN}============================================================${RESET}"
# example:  ./entrypoint.sh --input obfuscator/tests/logs_dir/ip_addr.log --salt abc123
docker run obfuscator "$@"
