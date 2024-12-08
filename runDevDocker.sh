#!/bin/bash
#
# Run to get a dev docker with torch environment using the
# Dockerfile in the repository so the transformer TTS can use GPU hardware
#

set -e

IMAGE_NAME="local-servant-llm:latest"
USER_ID=$(id -u)
GROUP_ID=$(id -g)

docker build --build-arg USER_ID=${USER_ID} --build-arg GROUP_ID=${GROUP_ID} -t ${IMAGE_NAME} .
docker run --rm -it --gpus all \
           -v ~/.cache/huggingface/hub:/home/servant/.cache/huggingface/hub \
           -v ~/nltk_data/:/home/servant/nltk_data/ \
           --privileged \
           -v "$(pwd)":/app ${IMAGE_NAME} bash