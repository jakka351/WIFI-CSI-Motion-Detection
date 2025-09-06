# WIFI-CSI-Motion-Detection
Detecting Motion via WIFI Channel State Information using a RPI4 with patched firmware.
**Use case:** Detect motion through walls using Wi-Fi signals and a Raspberry Pi by capturing Channel State Information (CSI) from 802.11 beacons.

![simplescreenrecorder-2025-09-06_16 43 06](https://github.com/user-attachments/assets/a2244efa-45d3-4d83-950f-599e2199b7c6)

---

## Table of Contents

1. [Introduction](#introduction)  
2. [Hardware Requirements](#hardware-requirements)  
3. [Setup](#setup)  
4. [Testing the Setup](#testing-the-setup)  
5. [Prepare the Python Environment](#prepare-the-python-environment)  
6. [Configure InfluxDB](#configure-influxdb)  
7. [Run the Wi-Fi Sensing Script](#run-the-wi-fi-sensing-script)  
8. [Credits](#credits)

---

## Introduction

This project demonstrates how Wi-Fi signals—specifically, CSI extracted from on-board Raspberry Pi Wi-Fi—can be used for detecting motion, even through walls, by analyzing reflections/absorption caused by the human body ([hackster.io](https://www.hackster.io/mzakharo/wifi-sensing-via-raspberry-pi-ff1087)).

**Notes:**
- CSI comes from OFDM-based 802.11 beacons; this works best in the 5 GHz band.
- On many routers, 2.4 GHz uses DSSS (not OFDM), which is less suitable.
- Use channels like **36/80** or **157/80**, which are commonly supported by default patches.
- This setup **disables on-board Wi-Fi communication**; make sure to use an Ethernet connection to access the Pi ([hackster.io](https://www.hackster.io/mzakharo/wifi-sensing-via-raspberry-pi-ff1087)).

---

## Hardware Requirements

- **Raspberry Pi 4 Model B** (or similar Pi with onboard Wi-Fi).

---

## Setup

1. Flash the **official 32-bit Raspbian image** onto your SD card.  
2. Update and upgrade packages:

   ```bash
   sudo apt-get update && sudo apt-get dist-upgrade
   sudo reboot


**This is a variation on code found in this guide**:  
**Credit:** Mikhail Zakharov, published December 20, 2021  
**License:** GPL-3.0+ ([https://www.hackster.io/mzakharo/wifi-sensing-via-raspberry-pi-ff1087](https://www.hackster.io/mzakharo/wifi-sensing-via-raspberry-pi-ff1087))


