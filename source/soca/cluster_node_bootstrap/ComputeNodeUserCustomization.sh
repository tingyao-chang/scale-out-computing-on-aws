#!/bin/bash -xe

# User customization code below
echo -e "umask 027" > /etc/profile.d/umask.sh

timedatectl set-timezone "Asia/Taipei"

echo "
## Track all commands run by root
-a exit,always -F arch=b64 -F euid=0 -S execve
-a exit,always -F arch=b32 -F euid=0 -S execve
" >> /etc/audit/rules.d/audit.rules