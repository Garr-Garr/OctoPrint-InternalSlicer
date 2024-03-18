#!/bin/bash
# https://github.com/OctoPrint/octoprint-docker

docker-compose rm -f
docker-compose pull
docker-compose up --build -d
