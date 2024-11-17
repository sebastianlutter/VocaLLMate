#!/bin/bash
#
# Script to run and stop all stacks at once. When
# executed without parameter status is shown.
#
cd "$(dirname $0)"

# Make sure that there is a docker swarm up and running, if not do so
docker node ls  &> /dev/null
if [ $? -ne 0 ]; then
  IP_ADDRESS=$(ip -4 addr show $(ip route get 8.8.8.8 | grep -oP 'dev \K\S+') | grep -oP 'inet \K\S+' | cut -d/ -f1)
  echo "Init swarm with IP $IP_ADDRESS"
  docker swarm init --advertise-addr $IP_ADDRESS
fi
# The stack is connected to an external network interface that is shared between all stacks on the server
docker network ls | grep servant-net &> /dev/null
if [ $? -ne 0 ]; then
  docker network create --attachable -d overlay servant-net
fi

title() {
  echo "##############################################################"
  echo "# $1"
  echo "##############################################################"
}

list_services() {
  docker compose ls
}

compose() {
  cd "$1"
  docker compose -f ${CONF} $2 $3 $4
  cd ..
}

ACTION="${1}"
# set device suffix
case "${2}" in
  cuda|nvidia|gpu)
    echo "Starting NVIDIA cuda stacks"
    DEVICE="-cuda"
    ;;
  rocm|amd)
    echo "Starting ROCm stacks (not implemented yet)"
    DEVICE="-rocm"
    ;;
  *)
    echo "Starting CPU only stacks"
    DEVICE=""
    ;;
esac
CONF="docker-compose${DEVICE}.yaml"
echo "Using $CONF files"

case "${ACTION}" in
  start)
    title "Starting all stacks"
    ;;
  stop)
    title "Stopping all stacks"
    ;;
  *)
    title "Show status"
    list_services
    ;;
esac

find . -type d -name "*-stack" | while read folder; do
  case "${ACTION}" in
    start)
       echo "Starting $folder"
       compose "$folder" up -d
      ;;
    stop)
       echo "Stop $folder"
       compose "$folder" down
      ;;
    *)
      title "Services of $folder"
      cd $folder
      docker compose ps --format "{{.Name}} {{.Image}} {{.Status}}" | while read NAME IMAGE STATUS; do
        echo -e "  - $IMAGE - $STATUS: $NAME"
      done
      cd ..
      ;;
  esac
done
