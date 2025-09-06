# WIFI-CSI-Motion-Detection
Detecting Motion via WIFI Channel State Information using a RPI4 with patched firmware.

WiFi Sensing via Raspberry Pi

Use case: Detect motion through walls using Wi-Fi signals and a Raspberry Pi by capturing Channel State Information (CSI) from 802.11 beacons.

Author: Mikhail Zakharov, published December 20, 2021
License: GPL-3.0+ 
Hackster

Table of Contents

Introduction

Hardware Requirements

Setup

Testing the Setup

Prepare the Python Environment

Configure InfluxDB

Run the Wi-Fi Sensing Script

Credits

Introduction

This project demonstrates how Wi-Fi signals—specifically, CSI extracted from on-board Raspberry Pi Wi-Fi—can be used for detecting motion, even through walls, by analyzing reflections/absorption caused by the human body 
Hackster
.

Notes:

CSI comes from OFDM-based 802.11 beacons; this works best in the 5 GHz band.

On many routers, 2.4 GHz uses DSSS (not OFDM), which is less suitable.

Use channels like 36/80 or 157/80, which are commonly supported by default patches.

This setup disables on-board Wi-Fi communication; make sure to use an Ethernet connection to access the Pi 
Hackster
.

Hardware Requirements

Raspberry Pi 4 Model B (or similar Pi with onboard Wi-Fi) 
Hackster
.

Setup

Flash the official 32-bit Raspbian image onto your SD card.

Update and upgrade packages:

sudo apt-get update && sudo apt-get dist-upgrade
sudo reboot


Enable CSI extraction by installing the Nexmon CSI patch:

Follow instructions at seemoo-lab/nexmon_csi.

If issues arise, consult nexmonster for helpful scripts. Note: as of December 20, 2021, nexmonster did not support kernel 5.10, which nexmon_csi supports 
Hackster
.

Build makecsiparams and place the binary in your $PATH for convenience 
Hackster
.

Testing the Setup

After patching and installing the CSI extractor, check system behavior:

COPYING brcmfmac43455-sdio.bin => /lib/firmware/brcm/brcmfmac43455-sdio.bin  
UNLOADING brcmfmac  
RELOADING brcmfmac


Configure the CSI capture:

makecsiparams -c 157/80 -C 1 -N 1 -b 0x80 m+IBEQGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==
ifconfig wlan0 up
# For channel 36/80 (alternative):
# nexutil -Iwlan0 -s500 -b -l34 -v KuABEQGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==
nexutil -Iwlan0 -s500 -b -l34 -v m+IBEQGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==
iw dev wlan0 interface add mon0 type monitor
ip link set mon0 up


Optionally, use MAC filtering if you're in a crowded Wi-Fi environment 
Hackster
.

Prepare the Python Environment

Install necessary dependencies:

sudo apt install libatlas-base-dev
pip3 install numpy influxdb-client
