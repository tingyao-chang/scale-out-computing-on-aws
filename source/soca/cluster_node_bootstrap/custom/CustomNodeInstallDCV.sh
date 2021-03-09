#!/bin/bash -xe

source /etc/environment
source /root/config.cfg

# Install Gnome or  Mate Desktop
if [[ $SOCA_BASE_OS == "rhel7" ]]
then
  yum groupinstall "Server with GUI" -y
elif [[ $SOCA_BASE_OS == "amazonlinux2" ]]
then
  yum install -y $(echo ${DCV_AMAZONLINUX_PKGS[*]})
  amazon-linux-extras install mate-desktop1.x
  bash -c 'echo PREFERRED=/usr/bin/mate-session > /etc/sysconfig/desktop'
else
  # Centos7
  yum groupinstall "GNOME Desktop" -y
fi

# Automatic start Gnome upon reboot
systemctl set-default graphical.target

# Download and Install DCV
cd ~
wget $DCV_URL
if [[ $(md5sum $DCV_TGZ | awk '{print $1}') != $DCV_HASH ]];  then
    echo -e "FATAL ERROR: Checksum for DCV failed. File may be compromised." > /etc/motd
    exit 1
fi

# Install DCV server and Xdcv
tar zxvf $DCV_TGZ
cd nice-dcv-$DCV_VERSION
rpm -ivh nice-xdcv-*.rpm --nodeps
rpm -ivh nice-dcv-server*.rpm --nodeps

# Configure DCV
mv /etc/dcv/default.perm /etc/dcv/default.perm.orig

echo -e """[groups]
[aliases]
[permissions]
%any% deny clipboard-copy clipboard-paste file-download file-upload usb printer smartcard
""" > /etc/dcv/default.perm

# Start DCV server
sudo systemctl enable dcvserver
sudo systemctl stop dcvserver
sleep 5
sudo systemctl start dcvserver

systemctl stop firewalld
systemctl disable firewalld

# Start X
systemctl isolate graphical.target

# Start Session
echo "Launching session ... : dcv create-session --user $SOCA_DCV_OWNER --owner $SOCA_DCV_OWNER --type virtual $SOCA_DCV_SESSION_ID"
dcv create-session --user $SOCA_DCV_OWNER --owner $SOCA_DCV_OWNER --type virtual $SOCA_DCV_SESSION_ID
echo $?
sleep 5

echo "@reboot dcv create-session --owner $SOCA_DCV_OWNER $SOCA_DCV_SESSION_ID # Do Not Delete"| crontab - -u $SOCA_DCV_OWNER
exit 0
