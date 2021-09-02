#!/usr/bin/python3
import sys
import configparser
import logging
import time
import socket, struct
import gi.repository.GLib
import dbus
import dbus.service
import uuid
import os
import subprocess

# global variables
global config
config = configparser.RawConfigParser()
global wanip
wanip = None


class IP():
    """
    This class facilitate to manipulate IP
    """

    def int_to_ip(self, ip_int):
        """
        This method return int into IP address
                
        :return:    Return int into IP address
        :rtype:    :class:`socket.inet_ntoa`
        """
        return socket.inet_ntoa(struct.pack("=I", ip_int))
        
    def ip_to_int(self, addr):
        """
        This method return IP address in int
                
        :return:    Return IP address as int
        :rtype:    Integer
        """
        return struct.unpack("!I", socket.inet_aton(addr))[0]
    
#######################################################################
#######################################################################
#######################################################################


def fetchWANIP():
    """
    This method will fetch and return WAN interface IP
    
    :return:    Return WAN IP
    :rtype:    String
    """
    logging.info("Trying to fetch WAN IP")
    _wanIf = config.get("interface", "wan")
    _wanip = None
    try:
        bus = dbus.SystemBus()
        proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
        manager = dbus.Interface(proxy, "org.freedesktop.NetworkManager")
        devices = manager.GetDevices()
        for device in devices:
            devProxy = bus.get_object("org.freedesktop.NetworkManager", device)
            devConfIface = dbus.Interface(devProxy, "org.freedesktop.DBus.Properties")
            devConf = devConfIface.GetAll("org.freedesktop.NetworkManager.Device")
            if devConf['Interface'] == _wanIf:
                actConProxy = bus.get_object("org.freedesktop.NetworkManager", devConf["ActiveConnection"])
                actConIface = dbus.Interface(actConProxy, "org.freedesktop.DBus.Properties")
                actConConf = actConIface.GetAll("org.freedesktop.NetworkManager.Connection.Active")
                actConIP4Proxy = bus.get_object("org.freedesktop.NetworkManager", actConConf['Ip4Config'])
                actConIP4Iface = dbus.Interface(actConIP4Proxy, "org.freedesktop.DBus.Properties")
                actConIP4Conf = actConIP4Iface.GetAll("org.freedesktop.NetworkManager.IP4Config")
                _wanip = actConIP4Conf["AddressData"][0]["address"]
                logging.info(f"WAN IP fetched for {_wanIf} - {_wanip}")
    except Exception as e:
        logging.error("Trying to fetch WAN IP error")
        logging.error(e)
    # return WAN IP
    return _wanip


def removeWIFIConnections():
    """
    This method will remove existing WIFI connections
    """
    logging.info("Trying to remove existing WIFI connections")
    wifiIF = config.get("interface", "wifi")
    try:
        bus = dbus.SystemBus()
        proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
        manager = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
        connections = manager.ListConnections()
        for connection in connections:
            conProxy = bus.get_object("org.freedesktop.NetworkManager", connection)
            settingsIface = dbus.Interface(conProxy, "org.freedesktop.NetworkManager.Settings.Connection")
            conSettings = settingsIface.GetSettings()
            if conSettings["connection"]["interface-name"] == wifiIF:
                settingsIface.Delete()
                logging.info(f"Deleted existing WIFI connection - {conSettings['connection']['id']}")
    except Exception as e:
        logging.error("Removing existing WIFI connections error")
        logging.error(e)


def createWIFIAccessPoint():
    """
    This method will create the access point
    """
    ifname = config.get("interface", "wifi")
    ipaddress = config.get("hotspot", "ip")
    prefix = int(config.get("hotspot", "prefix"))
    ssid = config.get("hotspot", "ssid")
    password = config.get("hotspot", "password")
    ################################
    s_wifi = dbus.Dictionary(
    {
        "ssid": dbus.ByteArray(ssid.encode("utf-8")),
        "mode": "ap",
    })
    s_wsec = dbus.Dictionary(
    {
        "key-mgmt": "wpa-psk",
        "psk": password
    })
    s_con = dbus.Dictionary(
        {"type": "802-11-wireless",
        "interface-name":ifname ,
        "uuid": str(uuid.uuid4()),
        "id": ssid,
        "autoconnect":dbus.Boolean(True)
        })
    addr1 = dbus.Dictionary({"address": ipaddress, "prefix": dbus.UInt32(prefix)})
    dns = []
    s_ip4 = dbus.Dictionary(
    {
        "address-data": dbus.Array([addr1], signature=dbus.Signature("a{sv}")),
        "dns": dbus.Array(dns, signature=dbus.Signature('u'), variant_level=1),
        "method": "manual",
    })
    s_ip6 = dbus.Dictionary({"method": "ignore"})
    con = dbus.Dictionary(
    {
        "802-11-wireless": s_wifi,
        "802-11-wireless-security":s_wsec,
        "connection": s_con,
        "ipv4": s_ip4,
        "ipv6": s_ip6
    })
    try:
        logging.info("Creating hotspot connection: {} - {}".format(s_con["id"], s_con["uuid"]))
        ##########
        bus = dbus.SystemBus()
        proxy = bus.get_object(
            "org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings"
        )
        settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
        connection = settings.AddConnection(con)
        logging.info(f"Created access point connection {connection}")
    except Exception as e:
        logging.error("Hotspot connection creation failed")
        logging.error(e)


def configureDHCP():
    """
    This method will configure DHCP using dnsmasq
    """
    dhcpStart = config.get("hotspot", "dhcpstart")
    dhcpEnd = config.get("hotspot", "dhcpend")
    dnsmasqConfig = f"""#PI Hotspot config
domain-needed
bogus-priv
dhcp-option=option:dns-server
dhcp-authoritative
dhcp-range={dhcpStart},{dhcpEnd},1h
"""
    confFile = open("/etc/dnsmasq.conf", "w")
    confFile.write(dnsmasqConfig)
    confFile.close()

    
def configureProxy():
    """
    This method will configure 3proxy
    """
    port = config.get("proxy", "port")
    allowedDomains = config.get("proxy", "alloweddomains")
    proxyConfig = f"""#!/bin/3proxy
#daemon
pidfile /var/run/3proxy.pid
chroot /usr/local/3proxy proxy proxy
nscache 65536
nserver 8.8.8.8
nserver 8.8.4.4
log /logs/3proxy-%y%m%d.log D
rotate 1
counter /count/3proxy.3cf
include /conf/counters
include /conf/bandlimiters
auth iponly
allow * * {allowedDomains}
deny *
proxy -e{wanip} -p{port}
"""
    confFile = open("/etc/3proxy/3proxy.cfg", "w")
    confFile.write(proxyConfig)
    confFile.close()

    
def startServices():
    """
    This method will start 3proxy and dnsmasq services
    """
    # dnsmasq
    out_dnsmasq = subprocess.run(["systemctl", "restart", "dnsmasq"], stdout=subprocess.PIPE)
    if out_dnsmasq.returncode == 0:
        logging.info("dnsmasq service started/restarted successfully")
    else:
        logging.error("dnsmasq service start restart error")
    # 3proxy
    out_3proxy = subprocess.run(["systemctl", "restart", "3proxy"], stdout=subprocess.PIPE)
    if out_3proxy.returncode == 0:
        logging.info("3proxy service started/restarted successfully")
    else:
        logging.error("3proxy service start restart error")


if __name__ == "__main__":
    """
    This is the main method call when executing the script
    """
    # log format
    logFormat = '%(asctime)s --  %(name)s::%(levelname)s -- %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=logFormat)
    # log format end
    # read the config file
    try:
        config.read("pihotspot.conf")
    except Exception as e:
        logging.error("Error while reading configurations file")
        logging.error(e)
        sys.exit(1)
    # Wait until fetch WAN IP
    while wanip is None:
        # try to fetch WAN IP
        wanip = fetchWANIP()
        # if not fetched sleep for 2 sec before next fetch
        if wanip is None:
            time.sleep(2)
    # WAN IP fetched
    # remove existing WIFI connections
    removeWIFIConnections()
    # create hotspot conenction
    createWIFIAccessPoint()
    # configure DHCP server
    configureDHCP()
    # configure 3proxy
    configureProxy()
    # start services
    startServices()
    # loop forever
    while True:
        time.sleep(15)
    # nmcli connection add type wifi ifname wlan0 con-name hotspot connection.autoconnect yes 
    # 802-11-wireless.mode ap 802-11-wireless.ssid pi-ap wifi-sec.key-mgmt wpa-psk wifi-sec.psk "PASSWORD" 
    # ipv4.method manual ipv4.addresses 192.168.1.1/24
    # DNSMASQ
    # /etc/dnsmasq.conf
    # domain-needed
    # bogus-priv
    # dhcp-option=option:dns-server,1.1.1.1
    # dhcp-authoritative
    # dhcp-range=192.168.1.100,192.168.1.250,1h
            
