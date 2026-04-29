@'
# 🗳️ Smart Voter Verification System

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-3B%2B-red.svg)](https://www.raspberrypi.org/)

## 📋 Overview

A complete **offline biometric voter verification system** built for the Election Commission using Face Recognition and Aadhaar verification on Raspberry Pi.

## 🎯 Features

| Role | Functions |
|------|-----------|
| **👑 Admin** | Full system control, voter management, reports, CSV export |
| **📝 Registrar** | Register new voters with live face capture |
| **🔍 Verifier** | 2-step verification (Aadhaar → Face Recognition) |

## 🖥️ Hardware Requirements

- Raspberry Pi 3 Model B+ (or higher)
- Pi Camera Module v2 / USB Webcam
- 7-inch Touchscreen (optional)
- 16GB+ MicroSD card

## 💻 Installation

### On Raspberry Pi

```bash
# Clone repository
git clone https://github.com/yogabalan07/Smart-voter-verification.git
cd Smart-voter-verification

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install opencv-python face_recognition pillow numpy

# Install system package
sudo apt install python3-pil python3-pil.imagetk -y

# Run application
python election_commision_complete.py
