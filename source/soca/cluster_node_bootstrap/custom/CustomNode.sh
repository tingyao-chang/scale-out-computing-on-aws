#!/bin/bash -xe

source /etc/environment
source /root/config.cfg

if [ $# -lt 1 ]
  then
    exit 0
fi

# Install CloudWatch Agent
if [[ $SOCA_BASE_OS == "centos7" ]]; then
    yum install -y https://s3.$AWS_DEFAULT_REGION.amazonaws.com/amazoncloudwatch-agent-$AWS_DEFAULT_REGION/centos/amd64/latest/amazon-cloudwatch-agent.rpm
elif [[ $SOCA_BASE_OS == "rhel7" ]]; then
    yum install -y https://s3.$AWS_DEFAULT_REGION.amazonaws.com/amazoncloudwatch-agent-$AWS_DEFAULT_REGION/redhat/amd64/latest/amazon-cloudwatch-agent.rpm
else # Amazon Linux 2
    yum install -y amazon-cloudwatch-agent
fi

# Start the CloudWatch Agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/apps/soca/$SOCA_CONFIGURATION/cluster_node_bootstrap/amazon-cloudwatch-agent.json

SCHEDULER_HOSTNAME=$1

# Install System required libraries
if [[ $SOCA_BASE_OS == "rhel7" ]];
then
    yum install -y $(echo ${SYSTEM_PKGS[*]} ${SCHEDULER_PKGS[*]}) --enablerepo rhui-REGION-rhel-server-optional
else
    yum install -y $(echo ${SYSTEM_PKGS[*]} ${SCHEDULER_PKGS[*]})
fi

yum install -y $(echo ${OPENLDAP_SERVER_PKGS[*]} ${SSSD_PKGS[*]})


# Edit path with new scheduler/python locations
echo "export PATH=\"/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/apps/soca/$SOCA_CONFIGURATION/python/latest/bin\"" >> /etc/environment

# Disable SELINUX
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

# Configure Host
SERVER_IP=$(hostname -I)
SERVER_HOSTNAME=$(hostname)
SERVER_HOSTNAME_ALT=$(echo $SERVER_HOSTNAME | cut -d. -f1)
echo $SERVER_IP $SERVER_HOSTNAME $SERVER_HOSTNAME_ALT >> /etc/hosts

# Configure Ldap
echo "URI ldap://$SCHEDULER_HOSTNAME" >> /etc/openldap/ldap.conf
echo "BASE $LDAP_BASE" >> /etc/openldap/ldap.conf

echo -e "[domain/default]
enumerate = True
autofs_provider = ldap
cache_credentials = True
ldap_search_base = $LDAP_BASE
id_provider = ldap
auth_provider = ldap
chpass_provider = ldap
sudo_provider = ldap
ldap_sudo_search_base = ou=Sudoers,$LDAP_BASE
ldap_uri = ldap://$SCHEDULER_HOSTNAME
ldap_id_use_start_tls = True
use_fully_qualified_names = False
ldap_tls_cacertdir = /etc/openldap/cacerts

[sssd]
services = nss, pam, autofs, sudo
full_name_format = %2\$s\%1\$s
domains = default

[nss]
homedir_substring = /data/home

[pam]

[sudo]
ldap_sudo_full_refresh_interval=86400
ldap_sudo_smart_refresh_interval=3600

[autofs]

[ssh]

[pac]

[ifp]

[secrets]" > /etc/sssd/sssd.conf


chmod 600 /etc/sssd/sssd.conf
systemctl enable sssd
systemctl restart sssd

echo | openssl s_client -connect $SCHEDULER_HOSTNAME:389 -starttls ldap > /root/open_ssl_ldap
mkdir /etc/openldap/cacerts/
cat /root/open_ssl_ldap | openssl x509 > /etc/openldap/cacerts/openldap-server.pem

authconfig --disablesssd --disablesssdauth --disableldap --disableldapauth --disablekrb5 --disablekrb5kdcdns --disablekrb5realmdns --disablewinbind --disablewinbindauth --disablewinbindkrb5 --disableldaptls --disablerfc2307bis --updateall
sss_cache -E
authconfig --enablesssd --enablesssdauth --enableldap --enableldaptls --enableldapauth --ldapserver=ldap://$SCHEDULER_HOSTNAME --ldapbasedn=$LDAP_BASE --enablelocauthorize --enablemkhomedir --enablecachecreds --updateall

echo "sudoers: files sss" >> /etc/nsswitch.conf

# Disable SELINUX & firewalld
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

systemctl stop firewalld
systemctl disable firewalld

# Disable StrictHostKeyChecking
echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
echo "UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

# Disable ulimit
echo -e  "
* hard memlock unlimited
* soft memlock unlimited
" >> /etc/security/limits.conf

# Reboot to disable SELINUX
sudo reboot
# Upon reboot, ComputenodePostReboot will be executed
