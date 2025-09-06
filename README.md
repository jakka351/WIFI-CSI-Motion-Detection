# WIFI-CSI-Motion-Detection
Detecting Motion via WIFI Channel State Information using a RPI4 with patched firmware.
**Use case:** Detect motion through walls using Wi-Fi signals and a Raspberry Pi by capturing Channel State Information (CSI) from 802.11 beacons.

![simplescreenrecorder-2025-09-06_16 43 06](https://github.com/user-attachments/assets/a2244efa-45d3-4d83-950f-599e2199b7c6)

---

## Table of Contents

1. [Introduction](#introduction)  
2. [Hardware Requirements](#hardware-requirements)  
3. [Setup](#setup)  
4. [Run the Wi-Fi Sensing Script](#run-the-wi-fi-sensing-script)
5. [Interpretation of Data Display](#interpretation-of-data-display)  
6. [Credits](#credits)

---

## Introduction

This project demonstrates how Wi-Fi signals—specifically, CSI extracted from on-board Raspberry Pi Wi-Fi—can be used for detecting motion, even through walls, by analyzing reflections/absorption caused by the human body.
**Notes:**
- CSI comes from OFDM-based 802.11 beacons; this works best in the 5 GHz band.
- On many routers, 2.4 GHz uses DSSS (not OFDM), which is less suitable.
- Use channels like **36/80** or **157/80**, which are commonly supported by default patches.
- This setup **disables on-board Wi-Fi communication**; make sure to use an Ethernet connection to access the Pi, alternatively use a second USB wifi dongle on WLAN1 to access the Pi.

---

## Hardware Requirements

- **Raspberry Pi 4 Model B** (or similar Pi with onboard Wi-Fi).
- **USB Wifi Adaptor**

---

## Setup

1. Flash **32 Bit Raspberry Pi - Legacy OS** onto your SD card. This is important as we need to patch the firmware of the Raspbery Pi.  
2. Update and upgrade packages:

   ```bash
   sudo apt update -y && sudo apt upgrade -y
   sudo reboot
   
3. Install picsi on a Raspberry Pi, which is a Python tool for installing and managing Nexmon CSI on Raspberry Pi:
   Ensure Python 3 and pip are installed: picsi requires Python 3.7 or newer. Raspberry Pi OS usually comes with Python 3 pre-installed. You'll also need pip for Python
   ```bash
   sudo apt install python3-pip
   pip3 install picsi
   ```
   Update your PATH (optional but recommended): To ensure the picsi command is readily available in your terminal, update your shell's PATH variable:
   ```bash
   source ~/.profile
   ```
   Install Nexmon CSI firmware/binaries: picsi handles the installation of Nexmon CSI, which involves downloading or compiling the necessary firmware and binaries for your specific Raspberry Pi model. Execute the following command:
   ```
   picsi install
   ```
   Enable picsi
   ```bash
   picsi enable
   ```
   This enables Nexmon CSI and starts CSI collection. You can view the status using picsi status or stop it with picsi down. 
   
5. Set Raspberry Pi Firmware for Channel State Information:
   ```bash init.sh
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
   ```
6. Create the python scripts, wifi_sensing.py & matrix.py
   ```bash
   located in the github repository
   ```
7. Create the script start.sh
   ```bash
   #/bin/bash
   python3 -u wifi_sensing.py | python3 matrix.py
   ```
8. Run the script
   ```bash
   sudo chmod +x ./start.sh
   ./start.sh
   ```

# Interpretation of Data Display


# Credis
**This is a variation on code found in this guide**:  
**Credit:** Mikhail Zakharov, published December 20, 2021  
**License:** GPL-3.0+ ([https://www.hackster.io/mzakharo/wifi-sensing-via-raspberry-pi-ff1087](https://www.hackster.io/mzakharo/wifi-sensing-via-raspberry-pi-ff1087))


