#!/bin/bash -xe

source /etc/environment
source /root/config.cfg
export PATH=$PATH:/usr/local/bin

REQUIRE_REBOOT=0
echo "SOCA > BEGIN PostReboot setup"

# Begin DCV Customization
if [[ "$SOCA_JOB_TYPE" == "dcv" ]]; then
    echo "Installing DCV"
    /bin/bash /apps/soca/$SOCA_CONFIGURATION/cluster_node_bootstrap/custom/CustomNodeInstallDCV.sh >> $SOCA_HOST_SYSTEM_LOG/CustomNodeInstallDCV.log 2>&1
    sleep 30
fi
# End DCV Customization

echo -e "umask 027" > /etc/profile.d/umask.sh

timedatectl set-timezone "Asia/Taipei"

echo "
## Track all commands run by root
-a exit,always -F arch=b64 -F euid=0 -S execve
-a exit,always -F arch=b32 -F euid=0 -S execve
" >> /etc/audit/rules.d/audit.rules

service auditd restart

# Unmount /apps after execution of ComputeNotePostReboot.sh
echo "sed -i '/apps/d' /etc/fstab" | at now + 1 minutes
echo "umount /apps" | at now + 1 minutes