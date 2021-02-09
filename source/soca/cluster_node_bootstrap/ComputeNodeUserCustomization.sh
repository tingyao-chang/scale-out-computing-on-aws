#!/bin/bash -xe

# User customization code below
echo -e "umask 027" > /etc/profile.d/umask.sh
timedatectl set-timezone "Asia/Taipei"