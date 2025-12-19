![Python](https://img.shields.io/badge/Python-3.x-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-Face%20Recognition-green)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-purple)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-Academic-lightgrey)

# 🎯 Face Recognition Attendance Management System

A **Python-based Face Recognition Attendance Management System** built using  
**Tkinter, OpenCV, and MySQL**.

This project allows users to **register students, collect face images, train a face recognition model, recognize faces in real time, and automatically mark attendance**.

---

## 📌 Features

### 👤 Student Management
- Add, update, and delete student details  
- Store student data securely in a MySQL database  

### 📸 Face Data Collection
- Capture multiple face images per student  
- Store images in a dataset folder  

### 🧠 Face Training
- Train face recognition model using **LBPH (OpenCV)**  
- Save trained model for future recognition  

### 🎥 Real-Time Face Recognition
- Webcam-based face detection and recognition  
- Fullscreen recognition mode  
- Adjustable confidence threshold  

### 📝 Attendance System
- Automatic attendance marking  
- Entry & exit time tracking  
- Export attendance reports to **CSV / PDF**  
- Remove duplicate attendance records  

### 🆘 Help & Chat Bot
- Built-in help tab with usage instructions  
- Rule-based chatbot for common queries  

---

## 📸 Application Screenshots

> Add your real screenshots inside the `screenshots/` folder

### 🏠 Main Dashboard
<img width="1752" height="929" alt="{4E255C23-E810-467C-B675-AB53EAD687AD}" src="https://github.com/user-attachments/assets/613be84d-b31a-44b2-b90a-5b9f530ef8b5" />

### 👨‍💻 Developer Profile
<img width="1760" height="866" alt="{7A84AFBD-3728-4B1D-8108-3B6D075B5C8F}" src="https://github.com/user-attachments/assets/0eb0ca6a-6a7f-40eb-993c-e1ede84dfc75" />


### 🎥 Face Recognition (Fullscreen)
<img width="1757" height="990" alt="{BDB7439F-406E-44EE-8D93-C30E1C3584DE}" src="https://github.com/user-attachments/assets/d9901bc9-2ff4-4ec8-9c2d-be4c107d97ac" />
<img width="1751" height="990" alt="{BAC41616-ECA5-43D2-B9F4-DAAC4EBE5DA4}" src="https://github.com/user-attachments/assets/3d29c948-d669-4640-96c5-89bb6d12d8d1" />


### 🧠 Live Face Detection


### 🔐 Login System
<img width="1758" height="900" alt="{90E3C37C-60E7-4FDF-BB26-DC936295ABAF}" src="https://github.com/user-attachments/assets/fa031cdf-1c5a-49b9-a798-bba98e8c4c92" />


### 🆘 Help & Chat Bot
<img width="1760" height="873" alt="{BB9D7F9E-DF97-4072-93DC-0FF72B283838}" src="https://github.com/user-attachments/assets/a1c244fc-ea89-46e2-83f7-1ffc8ceae5c2" />


---
🛠️ Technologies Used

Python 3

Tkinter – GUI

OpenCV – Face detection & recognition

Pillow (PIL) – Image handling

MySQL – Database

NumPy

ReportLab – PDF export

Matplotlib – Attendance graphs

## 🗂️ Project Structure

```bash
Face-Recognition-Attendance-System/
│
├── main.py                 # Main dashboard
├── student.py              # Student management
├── train.py                # Face training
├── face_recongntion.py     # Face recognition
├── attendance.py           # Attendance system
├── help.py                 # Help & chatbot
├── devloper.py             # Developer profile
│
├── data/                   # Face image dataset
├── trainer/                # Trained model files
├── image/                  # UI images
├── screenshots/            # Project screenshots
│
├── .env                    # Database configuration
├── requirements.txt        # Python dependencies
└── README.md
------



