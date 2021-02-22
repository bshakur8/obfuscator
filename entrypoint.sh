echo ":: Building Obfuscator docker container"
docker build -t obfuscator .
echo ":: Running Obfuscator"
sudo docker run obfuscator "$@"
