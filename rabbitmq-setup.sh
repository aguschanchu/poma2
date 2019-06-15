#!/usr/bin/env bash

# RabbitMQ config
sudo apt-key adv --keyserver "hkps.pool.sks-keyservers.net" --recv-keys "0x6B73A36E6026DFCA"
sudo apt-get install apt-transport-https
sudo tee /etc/apt/sources.list.d/bintray.rabbitmq.list <<EOF
deb https://dl.bintray.com/rabbitmq-erlang/debian bionic erlang-21.x
deb https://dl.bintray.com/rabbitmq/debian bionic main
EOF
sudo apt-get update -y
sudo apt-get install rabbitmq-server -y --fix-missing

sudo rabbitmqctl add_user agus Outreach3005
sudo rabbitmqctl add_vhost poma
sudo rabbitmqctl set_permissions -p poma agus ".*" ".*" ".*"
sudo rabbitmq-plugins enable rabbitmq_management