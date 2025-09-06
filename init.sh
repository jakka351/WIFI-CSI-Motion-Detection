#/bin/bash
# run at start up
#Run this script to setup your CSI parameters and bring up Mon0 - the monitoring interface on wlan0
makecsiparams -c 157/80 -C 1 -N 1 -b 0x80
# bring wlan0 up
sudo ifconfig wlan0 up
#
nexutil -Iwlan0 -s500 -b -l34 -v m+IBEQGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==
# create interface mon0
sudo iw dev wlan0 interface add mon0 type monitor
# set mon0 up
sudo ip link set mon0 up

## sudo apt install libatlas-base-dev
## pip3 install numpy influxdb-client
