#!/bin/bash
#
# Script to run and stop all stacks at once. When
# executed without parameter status is shown.
#
cd "$(dirname $0)"

# The stack is connected to an external network interface that is shared between all stacks on the server
docker network ls | grep servant-net &> /dev/null
if [ $? -ne 0 ]; then
  docker network create -d overlay servant-net
fi


title() {
  echo "##############################################################"
  echo "# $1"
  echo "##############################################################"
}

list_services() {
  cd "$1"
  docker compose ls | tail -n+2
  cd ..
}

list_head() {
  #cd llm-stack
  #docker compose ls | head -n1
  #cd ..
  echo "NAME                STATUS              CONFIG FILES"
}

compose() {
  cd "$1"
  docker compose $2 $3 $4
  cd ..
}

ACTION="${1}"

case "${ACTION}" in
  start)
    title "Starting all stacks"
    ;;
  stop)
    title "Stopping all stacks"
    ;;
  *)
    title "Show status"
    list_head
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
      # Show running status if no parameter given
      list_services "$folder"
      ;;
  esac
done
