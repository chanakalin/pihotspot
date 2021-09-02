# PI Hotspot
PI Hotspot is a small wifi hotspot with a proxy to limit access combining NetworkManager, dnsmasq and [3proxy](https://3proxy.ru/).


## Installation
You need a Raspberry PI or Raspberry PI zero with WiFi enabled with Raspbian / Raspberry PI OS installed. To continue installation copy installer directory **pihotspot** to **/pihotspot**. Switch as root user, make **install.sh** installer script executable and execute it.

```bash
sudo -s
cd /pihotspot
chmod +x install.sh
./install.sh
```

To complete installation make sure to configure pihotspot configurations in **/pihotspot/pihotspot.conf** reboot the system.


## Configurations file
Configurations are in **/pihotspot/pihotspot.conf**. 

### Interfaces
Interfaces section you need to configure **WAN** interface and the **WIFI** interface which need to be configured as a hotspot ( access point )

```
[interface]
wan=eth0
wifi=wlan0
```

### Hotspot
Hotspot (access point) configurations are as follows.

| Configuration | Description |
| ------------- | ----------- |
| ip | IP address of the hotspot (access point) |
| prefix | Network prefix for the hotspot (access point) |
| dhcpstart | Start IP of the DHCP pool |
| dhcpend | End IP of the DHCP pool |
| ssid | WiFi SSID |
| password | WiFi hotspot (access point) password |


```
[hotspot]
ip=192.168.1.1
prefix=24
dhcpstart=192.168.1.100
dhcpend=192.168.1.250
ssid=pi-hotspot
password=PASSWORD
```

### Proxy
**port** is the proxy port. **alloweddomains** is for configure domains which are allowed to access over the proxy.
Make sure to deparate domains using **","** and all domains are in a single line.

eg:- google.com,*.google.com

### Example configurations file

```
[interface]
wan=eth0
wifi=wlan0

[hotspot]
ip=192.168.1.1
prefix=24
dhcpstart=192.168.1.100
dhcpend=192.168.1.250
ssid=pi-hotspot
password=PASSWORD

[proxy]
port=3128
alloweddomains=google.com,*.google.com
```


## Manage pihotspot service
**pihotspot** can manage using systemctl.

* systemctl stop pihotspot
* systemctl start pihotspot

