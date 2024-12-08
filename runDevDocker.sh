#!/usr/bin
#
# Run to get a dev docker with torch environment using the
# Dockerfile in the repository
#
IMAGE_NAME="local-servant-llm:latest"

docker build -t $IMAGE_NAME .

docker run --rm -it -v "$(pwd)":/app $IMAGE_NAME bash