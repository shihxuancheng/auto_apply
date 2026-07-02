#!/bin/bash

source /etc/profile
source ~/.profile
source ~/.bashrc
source /etc/bash.bashrc
cd /home/ubuntu/projects/auto_apply
uv run auto-apply -c ./config-sample.ini
