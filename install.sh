#!/bin/bash

function preInstallation {
    #Install required packages
    apt-get --allow-releaseinfo-change-suite update -y
    apt-get install -y vim git make gcc dnsmasq net-tools network-manager python3 python3-pip python3-dev python3-dbus libcairo2 libcairo-gobject2 libcairo2-dev apache2-utils
    
    #Disable & mask squid if present
    systemctl disable squid
    systemctl mask squid
    
    #Install python packages
    pip3 install -r requirements.txt
    
    #Disable network interface renaming by kernel
    echo -n " net.ifnames=0" >> /boot/cmdline.txt
    
    #Set network-manager as network connection manager
    echo "denyinterfaces wlan0" >> /etc/dhcpcd.conf
    echo "denyinterfaces eth0" >> /etc/dhcpcd.conf
    sed -i 's/managed=false/managed=true/' /etc/NetworkManager/NetworkManager.conf
    
    #enable IP forwarding if not
    if [ $(cat /proc/sys/net/ipv4/ip_forward) -eq 0 ];
    then
        echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf;
    fi

	#clone 3proxy, build and install
	git clone https://github.com/3proxy/3proxy.git
	cd 3proxy
	cp Makefile.Linux Makefile
	make
	make install
	# disable startup at boot and stop
	systemctl disable 3proxy
	systemctl stop 3proxy
	
	# disable startup at boot and stop dnsmasq
	systemctl disable dnsmasq
	systemctl stop dnsmasq
}
    

function postConfiguration {
    #link & enable service
    ln -s /pihotspot/pihotspot.service /usr/lib/systemd/system/
    systemctl enable pihotspot
	systemctl start pihotspot
}

#Install & configure
cd /pihotspot
preInstallation
postConfiguration