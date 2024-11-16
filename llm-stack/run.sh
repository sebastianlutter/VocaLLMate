#!/bin/bash

cd "$(dirname $0)"

# The stack is connected to an external network interface that is shared between all stacks on the server
docker network ls | grep servant-net &> /dev/null
if [ $? -ne 0 ]; then
  docker network create -d overlay servant-net
fi

docker compose -f docker-compose.yaml up -d
