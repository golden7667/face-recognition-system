from tkinter import *
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageTk, ImageOps
import os
from dotenv import load_dotenv
import cv2
import threading
import time
import mysql.connector
from datetime import datetime, date
import csv
import re
import traceback

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASS", "golden123")
DB_NAME = os.environ.get("DB_NAME", "facedb")

DEBUG_PREDICTIONS = False
 
def get_db_connection(parent=None):
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4"
        )
        return conn
    except Exception as e:
        if parent:
            try:
                messagebox.showerror("DB Error", f"Could not connect to database:\n{e}", parent=parent)
            except Exception:
                print("DB Error:", e)
        else:
            print("DB Error:", e)
        return None

def ensure_attendance_tables(parent=None):
    """
    Create tables if missing.
    """
    # create database 
    try:
        tmp = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, charset="utf8mb4")
        cur_tmp = tmp.cursor()
        try:
            cur_tmp.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            tmp.commit()
        except Exception:
            pass
        try:
            cur_tmp.close()
        except Exception:
            pass
        try:
            tmp.close()
        except Exception:
            pass
    except Exception:
        pass

    conn = get_db_connection(parent=parent)
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        # backward
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(64),
                name VARCHAR(255),
                timestamp DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        # sessions table:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(64),
                name VARCHAR(255),
                entry_time DATETIME,
                exit_time DATETIME,
                thumb_path VARCHAR(1024),
                class_name VARCHAR(255),
                present TINYINT(1) DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        # events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recorded_at DATETIME,
                event_type VARCHAR(32),
                student_id VARCHAR(64),
                name VARCHAR(255),
                entry_time DATETIME,
                exit_time DATETIME,
                thumb_path VARCHAR(1024),
                class_name VARCHAR(255),
                INDEX (student_id),
                INDEX (recorded_at),
                INDEX (class_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        return True
    except Exception as e:
        if parent:
            try:
                messagebox.showerror("DB Error", f"Could not create attendance tables:\n{e}", parent=parent)
            except Exception:
                print("DB Error:", e)
        else:
            print("DB Error:", e)
        return False
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def insert_session_entry_db(student_id: str, name: str, entry_time: datetime, thumb_path: str, class_name: str, parent=None):
    """
    Insert attendance_sessions row with present=1.
    Returns (ok, inserted_id_or_err)
    """
    conn = get_db_connection(parent=parent)
    if conn is None:
        return False, "DB connection failed"
    cursor = None
    try:
        cursor = conn.cursor()
        sql = """INSERT INTO attendance_sessions
                 (student_id, name, entry_time, thumb_path, class_name, present)
                 VALUES (%s,%s,%s,%s,%s,%s)"""
        cursor.execute(sql, (str(student_id), str(name), entry_time, thumb_path, class_name, 1))
        conn.commit()
        inserted_id = cursor.lastrowid
        return True, inserted_id
    except Exception as e:
        return False, str(e)
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def insert_event_db(row, parent=None):
    """
    Insert attendance_events row.
    row format: (timestamp,event,student_id,name,entry_time,exit_time,thumb_path,class_name)
    """
    try:
        recorded_at_text = row[0] or ""
        event_type = row[1] or ""
        student_id = row[2] or ""
        name = row[3] or ""
        entry_text = row[4] or ""
        exit_text = row[5] or ""
        thumb_path = row[6] or ""
        class_name = row[7] or ""
        def parse_dt(t):
            if not t:
                return None
            try:
                return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    return datetime.fromisoformat(t)
                except Exception:
                    return None
        recorded_at = parse_dt(recorded_at_text) or datetime.now()
        entry_time = parse_dt(entry_text)
        exit_time = parse_dt(exit_text)
    except Exception as e:
        return False, f"Row normalization failed: {e}"

    conn = get_db_connection(parent=parent)
    if conn is None:
        return False, "DB connection failed"
    cursor = None
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO attendance_events
            (recorded_at, event_type, student_id, name, entry_time, exit_time, thumb_path, class_name)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(sql, (recorded_at, event_type, str(student_id), str(name), entry_time, exit_time, thumb_path, class_name))
        conn.commit()
        return True, cursor.lastrowid
    except Exception as e:
        return False, str(e)
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

class FullscreenRecognizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition - Fullscreen")
        self.root.state('zoomed')  
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.confirm_exit())

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.header_h = max(80, int(self.screen_h * 0.12))
        self.title_h = max(48, int(self.screen_h * 0.07))

        # header images
        header_paths = [
            "image/G2CM_FI454_Learn_Article_Images_[Facial_recognition]_V1a-1.webp",
            "image/ggggg.jpg.webp",
            "image/Ethical-Hacking.jpg",
            "image/resized_Chatobots-legal-key-issues.jpg",
        ]
        self.header_photos = []
        header_w_each = max(1, self.screen_w // 4)
        for i, path in enumerate(header_paths):
            img = self.safe_open_image(path, (header_w_each, self.header_h), keep_aspect=True)
            photo = ImageTk.PhotoImage(img)
            self.header_photos.append(photo)
            Label(self.root, image=photo, bd=0).place(x=i * header_w_each, y=0, width=header_w_each, height=self.header_h)

        Label(self.root, text="Face Recognition (Fullscreen)", font=("Arial", max(18, self.title_h // 3), "bold"),
              fg="white", bg="black").place(x=0, y=self.header_h, width=self.screen_w, height=self.title_h)

        # layout
        content_y = self.header_h + self.title_h
        content_h = self.screen_h - content_y
        left_w = int(self.screen_w * 0.6)
        right_w = self.screen_w - left_w

        
        bg_path = "image/e6cdef00-99ef-11e9-90d0-c64097fc903d.jpeg"
        bg_img = self.safe_open_image(bg_path, (left_w, content_h), keep_aspect=True)
        self.bg_photo = ImageTk.PhotoImage(bg_img)
        self.left_label = Label(self.root, image=self.bg_photo, bd=0)
        self.left_label.place(x=0, y=content_y, width=left_w, height=content_h)

        # right frame
        right_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        right_frame.place(x=left_w, y=content_y, width=right_w, height=content_h)

        Label(right_frame, text="Controls & Status", font=("Arial", 20, "bold"), bg="white").pack(pady=6)

        
        meta_frame = Frame(right_frame, bg="white")
        meta_frame.pack(pady=4, fill=X, padx=12)
        Label(meta_frame, text="Class:", bg="white").pack(side=LEFT)
        self.class_entry = Entry(meta_frame, width=24)
        self.class_entry.pack(side=LEFT, padx=6)

        # buttons
        btn_frame = Frame(right_frame, bg="white")
        btn_frame.pack(pady=6)
        self.start_btn = Button(btn_frame, text="Start Recognition", font=("Arial", 12, "bold"),
                                bg="green", fg="white", width=16, command=self.start_recognition)
        self.start_btn.grid(row=0, column=0, padx=6)
        self.stop_btn = Button(btn_frame, text="Stop Recognition", font=("Arial", 12, "bold"),
                               bg="red", fg="white", width=16, state=DISABLED, command=self.stop_recognition)
        self.stop_btn.grid(row=0, column=1, padx=6)
        self.exit_btn = Button(btn_frame, text="Exit", font=("Arial", 12, "bold"),
                               bg="#444", fg="white", width=10, command=self.confirm_exit)
        self.exit_btn.grid(row=0, column=2, padx=6)

        # threshold
        controls2 = Frame(right_frame, bg="white")
        controls2.pack(pady=6, fill=X, padx=12)
        thr_frame = Frame(controls2, bg="white")
        thr_frame.pack(side=LEFT, fill=X, expand=True)
        Label(thr_frame, text="Confidence threshold (lower=stricter)", bg="white").pack(anchor=W)
        self.threshold_var = IntVar(value=60)
        self.threshold_slider = Scale(thr_frame, from_=0, to=200, orient=HORIZONTAL, variable=self.threshold_var)
        self.threshold_slider.pack(fill=X)

        #summary controls
        export_frame = Frame(right_frame, bg="white")
        export_frame.pack(pady=6, fill=X, padx=12)
        self.export_btn = Button(export_frame, text="Export Attendance CSV", command=self.export_csv)
        self.export_btn.pack(anchor=W, side=LEFT, padx=(0, 6))
        self.manual_btn = Button(export_frame, text="Add Manual Entry", command=self.manual_entry_popup)
        self.manual_btn.pack(anchor=W, side=LEFT, padx=(0, 6))
        self.summary_btn = Button(export_frame, text="Compute Attendance Summary", command=self.compute_attendance_summary)
        self.summary_btn.pack(anchor=W, side=LEFT, padx=(6,6))
        self.clear_today_btn = Button(export_frame, text="Clear Today's Attendance", command=self.clear_todays_attendance)
        self.clear_today_btn.pack(anchor=W, side=LEFT, padx=(6, 6))
        self.dedupe_db_btn = Button(export_frame, text="Remove Duplicate Records (DB)", command=self.remove_duplicate_db)
        self.dedupe_db_btn.pack(anchor=W, side=LEFT, padx=(6, 6))

        # autosave controls
        autosave_frame = Frame(right_frame, bg="white")
        autosave_frame.pack(pady=4, fill=X, padx=12)
        self.autosave_var = IntVar(value=1)
        self.autosave_chk = Checkbutton(autosave_frame, text="Enable Autosave (daily + global)", variable=self.autosave_var, bg="white")
        self.autosave_chk.pack(side=LEFT)
        Label(autosave_frame, text="Interval (sec):", bg="white").pack(side=LEFT, padx=(6,2))
        self.autosave_interval = IntVar(value=60)
        self.autosave_entry = Entry(autosave_frame, width=6, textvariable=self.autosave_interval)
        self.autosave_entry.pack(side=LEFT, padx=(0,6))

        # search
        search_frame = Frame(right_frame, bg="white")
        search_frame.pack(pady=6, fill=X, padx=12)
        Label(search_frame, text="Search:", bg="white").pack(side=LEFT)
        self.search_entry = Entry(search_frame, width=22)
        self.search_entry.pack(side=LEFT, padx=6)
        self.search_btn = Button(search_frame, text="Find", command=self.search_attendance)
        self.search_btn.pack(side=LEFT, padx=6)


        self.result_label = Label(right_frame, text="Waiting to start...", font=("Arial", 14), fg="blue", bg="white", wraplength=right_w - 40, justify=LEFT)
        self.result_label.pack(pady=12, padx=12, anchor=W)

        thumb_frame = Frame(right_frame, bg="white", bd=1, relief=RIDGE)
        thumb_frame.pack(padx=12, pady=6, fill=X)
        Label(thumb_frame, text="Recent Faces", bg="white", font=("Arial", 12, "bold")).pack(anchor=W, padx=6)
        self.thumb_strip = Frame(thumb_frame, bg="white")
        self.thumb_strip.pack(padx=6, pady=6, fill=X)
        self.max_thumbs = 6
        self.thumbnail_images = []
        self.thumb_labels = []
        for i in range(self.max_thumbs):
            lbl = Label(self.thumb_strip, image=None, bg="#eee", width=80, height=80, bd=1, relief=RIDGE)
            lbl.pack(side=LEFT, padx=4)
            self.thumb_labels.append(lbl)

        Label(right_frame, text="Attendance Log (recent):", bg="white").pack(anchor=W, padx=12, pady=(8,0))
        self.attendance_text = Text(right_frame, height=10, state=DISABLED, bg="#f7f7f7")
        self.attendance_text.pack(padx=12, pady=6, fill=X)

        
        status_h = int(self.screen_h * 0.04)
        self.status_frame = Frame(self.root, bg="#222")
        self.status_frame.place(x=0, y=self.screen_h - status_h, width=self.screen_w, height=status_h)
        self.status_label = Label(self.status_frame, text="Status: Ready", anchor=W, bg="#222", fg="white", font=("Arial", 12))
        self.status_label.place(x=6, y=0, width=int(self.screen_w * 0.6), height=status_h)
        self.clock_label = Label(self.status_frame, text="", anchor=E, bg="#222", fg="white", font=("Arial", 12))
        self.clock_label.place(x=int(self.screen_w * 0.6) + 10, y=0, width=int(self.screen_w * 0.4) - 16, height=status_h)

        # state
        self.cap = None
        self.video_running = False
        self.thread = None
        self.recognizer = None
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if self.face_cascade.empty():
            try:
                messagebox.showwarning("Warning", "Failed to load Haar cascade; detection may fail.", parent=self.root)
            except Exception:
                print("Warning: failed to load Haar cascade")

        self.label_map = {}
        self.sid_to_name = {}
        self.current_photo = None

    
        self.active_sessions = {}

        
        self.attendance_rows = []

        ensure_attendance_tables(parent=self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # clock
        self.update_clock()
        self._autosave_after_id = None
        self.start_autosave_loop_if_enabled()

    # safe image 
    def safe_open_image(self, path, size, keep_aspect=False):
        try:
            img = Image.open(path).convert("RGBA")
        except Exception:
            img = Image.new("RGBA", size, (180,180,180,255))
            return img.convert("RGB")
        if keep_aspect:
            img = ImageOps.contain(img, size, method=Image.LANCZOS)
            bg = Image.new("RGBA", size, (255,255,255,255))
            x = (size[0] - img.width)//2
            y = (size[1] - img.height)//2
            bg.paste(img, (x,y), img if img.mode=="RGBA" else None)
            return bg.convert("RGB")
        else:
            return img.resize(size, Image.LANCZOS).convert("RGB")

    def update_clock(self):
        now = datetime.now()
        try:
            self.clock_label.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            pass
        self.root.after(1000, self.update_clock)

    
    def load_label_map(self):
        labels_path = os.path.join("trainer","labels.txt")
        if not os.path.exists(labels_path):
            try:
                messagebox.showerror("Error", f"Labels file not found:\n{labels_path}\nTrain data first.", parent=self.root)
            except Exception:
                print(f"Labels file not found: {labels_path}")
            return None
        label_to_sid = {}
        try:
            with open(labels_path,"r",encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line:
                        continue
                    parts=line.split(",",1)
                    if len(parts)!=2:
                        continue
                    label_int=int(parts[0])
                    sid=parts[1].strip()
                    label_to_sid[label_int]=sid
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Could not read labels file:\n{e}", parent=self.root)
            except Exception:
                print("Could not read labels file:", e)
            return None
        return label_to_sid

    
    def load_student_names(self):
        conn = get_db_connection(parent=self.root)
        if conn is None:
            return None
        sid_to_name={}
        cursor=None
        try:
            cursor=conn.cursor()
            cursor.execute("SELECT `id`,`name` FROM `student`")
            rows=cursor.fetchall()
            for sid,name in rows:
                sid_to_name[str(sid)]=name
            return sid_to_name
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Could not load student names:\n{e}", parent=self.root)
            except Exception:
                print("Could not load student names:", e)
            return None
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # camera open 
    def open_camera_try(self, max_index=3, width=640, height=480, try_backends=True):
        backends = [0]
        if try_backends:
            try:
                backends = []
                if hasattr(cv2, "CAP_DSHOW"):
                    backends.append(cv2.CAP_DSHOW)
                if hasattr(cv2, "CAP_MSMF"):
                    backends.append(cv2.CAP_MSMF)
                backends.append(0)
            except Exception:
                backends = [0]

        for backend in backends:
            for idx in range(0, max_index + 1):
                cap = None
                try:
                    if backend and backend != 0:
                        cap = cv2.VideoCapture(idx, backend)
                    else:
                        cap = cv2.VideoCapture(idx)
                    if not cap or not cap.isOpened():
                        try:
                            if cap:
                                cap.release()
                        except Exception:
                            pass
                        continue
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass
                    ret, _ = cap.read()
                    if not ret:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        continue
                    return cap
                except Exception:
                    try:
                        if cap:
                            cap.release()
                    except Exception:
                        pass
                    continue
        return None

    def start_recognition(self):
        if self.video_running:
            return
        model_path = os.path.join("trainer","classifier.xml")
        if not os.path.exists(model_path):
            messagebox.showerror("Error", f"Model file not found:\n{model_path}\nTrain data first.", parent=self.root)
            return
        self.label_map = self.load_label_map()
        if self.label_map is None:
            return
        self.sid_to_name = self.load_student_names()
        if self.sid_to_name is None:
            return
        try:
            if hasattr(cv2,'face') and hasattr(cv2.face,'LBPHFaceRecognizer_create'):
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            else:
                raise AttributeError("cv2.face.LBPHFaceRecognizer_create not available")
            self.recognizer.read(model_path)
        except AttributeError:
            messagebox.showerror("Error","cv2.face.LBPHFaceRecognizer_create is not available.\nInstall opencv-contrib-python", parent=self.root)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model:\n{e}", parent=self.root)
            return

        self.status_label.config(text="Status: Opening camera...")
        cap = self.open_camera_try(max_index=3, width=640, height=480, try_backends=True)
        if cap is None:
            try:
                cap = cv2.VideoCapture(0)
                if not cap or not cap.isOpened():
                    raise RuntimeError("Fallback camera open failed")
            except Exception:
                messagebox.showerror("Error","Cannot open webcam. Ensure it is connected and not used by another application.", parent=self.root)
                return

        self.cap = cap
        self.video_running = True
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.status_label.config(text="Status: Camera running")
        self.thread = threading.Thread(target=self._video_loop, daemon=True)
        self.thread.start()

    def stop_recognition(self):
        if not self.video_running:
            return
        self.video_running = False
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.status_label.config(text="Status: Stopping camera...")
        try:
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except Exception:
                    pass
        except Exception:
            pass
        self.cap = None
        try:
            self.left_label.config(image=self.bg_photo)
            self.current_photo = None
            self.result_label.config(text="Recognition stopped.")
            self.status_label.config(text="Status: Camera stopped")
        except Exception:
            pass

    def on_close(self):
        self.stop_recognition()
        if self._autosave_after_id:
            try:
                self.root.after_cancel(self._autosave_after_id)
            except Exception:
                pass
        
        try:
            self.perform_autosave(final=True)
        except Exception:
            pass
        time.sleep(0.1)
        try:
            self.root.destroy()
        except Exception:
            try:
                self.root.quit()
            except Exception:
                pass
 
    def _video_loop(self):
        try:
            while self.video_running:
                if not self.cap or not self.cap.isOpened():
                    time.sleep(0.2)
                    continue

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                try:
                    threshold = float(self.threshold_var.get())
                except Exception:
                    threshold = 60.0

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = []
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50,50))

                detected_text = "No face detected"

                for (x,y,w,h) in faces:
                    roi_gray = gray[y:y+h, x:x+w]
                    try:
                        roi_gray_resized = cv2.resize(roi_gray, (200,200))
                    except Exception:
                        roi_gray_resized = roi_gray

                    try:
                        label_int, confidence = self.recognizer.predict(roi_gray_resized)
                    except Exception:
                        label_int, confidence = -1, float('inf')

                    if DEBUG_PREDICTIONS:
                        print(f"Predict -> label={label_int}, conf={confidence}")

                    if confidence <= threshold and label_int in self.label_map:
                        sid = self.label_map[label_int]
                        name = self.sid_to_name.get(str(sid), "Unknown")
                        percent = max(0, min(100, round(100 - confidence)))
                        detected_text = f"ID: {sid}, {name} ({percent}%)"
                        color = (0,255,0)
                        now = datetime.now()

                        sess = self.active_sessions.get(sid)
                        if not sess:
                            thumb_path = self._save_thumbnail_for_sid(frame[y:y+h, x:x+w], sid)
                            ok, inserted = insert_session_entry_db(sid, name, now, thumb_path, self.class_entry.get().strip(), parent=self.root)
                            session_id = inserted if ok else None
                            self.active_sessions[sid] = {"entry_time": now, "last_seen": now, "session_id": session_id, "thumb_path": thumb_path, "name": name}
                            # record entry event
                            self._record_event_row("entry", sid, name, now, None, thumb_path, self.class_entry.get().strip())
                        else:
                            sess['last_seen'] = now
                    else:
                        detected_text = f"Unknown (conf={round(confidence,1)})"
                        color = (0,0,255)

                    try:
                        cv2.rectangle(frame,(x,y),(x+w,y+h), color,2)
                        cv2.putText(frame, detected_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color,2)
                    except Exception:
                        pass

                self.result_label.after(0, lambda t=detected_text: self.result_label.config(text=t))

                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    left_w = int(self.screen_w * 0.6)
                    left_h = self.screen_h - (self.header_h + self.title_h)
                    frame_rgb = cv2.resize(frame_rgb, (left_w, left_h), interpolation=cv2.INTER_AREA)
                    img = Image.fromarray(frame_rgb)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.current_photo = imgtk
                    self.left_label.config(image=imgtk)
                except Exception:
                    pass

                time.sleep(0.02)
        except Exception as e:
            try:
                self.result_label.after(0, lambda: messagebox.showerror("Error", f"Error during video loop:\n{e}", parent=self.root))
            except Exception:
                print("Error during video loop:", e)
        finally:
            try:
                if self.cap and self.cap.isOpened():
                    try:
                        self.cap.release()
                    except Exception:
                        pass
            except Exception:
                pass
            self.cap = None
            self.video_running = False
            try:
                self.start_btn.after(0, lambda: self.start_btn.config(state=NORMAL))
                self.stop_btn.after(0, lambda: self.stop_btn.config(state=DISABLED))
                self.status_label.after(0, lambda: self.status_label.config(text="Status: Camera stopped"))
                self.result_label.after(0, lambda: self.result_label.config(text="Recognition stopped."))
            except Exception:
                pass
 
    def _save_thumbnail_for_sid(self, face_bgr, sid):
        try:
            os.makedirs("autosave/thumbs", exist_ok=True)
            class_name = self.class_entry.get().strip() or "global"
            folder = os.path.join("autosave","thumbs", class_name)
            os.makedirs(folder, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"{ts}_{sid}.jpg"
            path = os.path.join(folder, fname)
            try:
                face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(face_rgb)
                pil = pil.resize((200,200), Image.LANCZOS)
                pil.save(path, quality=85)
            except Exception:
                cv2.imwrite(path, face_bgr)
            return path
        except Exception:
            return ""

    def _record_event_row(self, event, sid, name, entry_time, exit_time, thumb_path, class_name):
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        entry_ts = entry_time.strftime("%Y-%m-%d %H:%M:%S") if entry_time else ""
        exit_ts = exit_time.strftime("%Y-%m-%d %H:%M:%S") if exit_time else ""
        class_name_safe = class_name or "global"
        row = (ts, event, str(sid), str(name), entry_ts, exit_ts, thumb_path or "", class_name_safe)
        self.attendance_rows.append(row)
        try:
            self._append_row_to_autosave_files(row, class_name_safe)
        except Exception as e:
            print("Immediate append failed:", e)
        try:
            ok, res = insert_event_db(row, parent=self.root)
            if not ok:
                print("Insert event DB failed:", res)
        except Exception as e:
            print("Insert event DB exception:", e)
        if event == "entry":
            display = f"{ts}  |  ENTRY  |  {sid}  |  {name}  |  entry={entry_ts}\n"
        else:
            display = f"{ts}  |  {event.upper()}  |  {sid}  |  {name}  |  entry={entry_ts} exit={exit_ts}\n"
        try:
            self.attendance_text.config(state=NORMAL)
            self.attendance_text.insert(END, display)
            self.attendance_text.see(END)
            self.attendance_text.config(state=DISABLED)
        except Exception:
            pass
        # thumbnail strip
        if thumb_path:
            try:
                pil = Image.open(thumb_path).convert("RGB")
                min_side = min(pil.width, pil.height)
                left = (pil.width - min_side)//2
                top = (pil.height - min_side)//2
                pil = pil.crop((left, top, left+min_side, top+min_side)).resize((80,80), Image.LANCZOS)
            except Exception:
                pil = Image.new("RGB",(80,80),(200,200,200))
            try:
                imgtk = ImageTk.PhotoImage(pil)
                self.thumbnail_images.insert(0, imgtk)
                if len(self.thumbnail_images) > self.max_thumbs:
                    self.thumbnail_images = self.thumbnail_images[:self.max_thumbs]
                for i, lbl in enumerate(self.thumb_labels):
                    if i < len(self.thumbnail_images):
                        lbl.config(image=self.thumbnail_images[i])
                        lbl.image = self.thumbnail_images[i]
                    else:
                        lbl.config(image='', bg="#eee")
            except Exception:
                pass

    def _append_row_to_autosave_files(self, row, class_name):
        class_name_safe = class_name or "global"
        base_dir = os.path.join("autosave", class_name_safe)
        os.makedirs(base_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(base_dir, f"{today_str}_attendance.csv")
        global_path = os.path.join(base_dir, "attendance_log.csv")
        write_daily_header = not os.path.exists(daily_path)
        write_global_header = not os.path.exists(global_path)
        with open(daily_path,"a",newline="",encoding="utf-8") as fd:
            w=csv.writer(fd)
            if write_daily_header:
                w.writerow(["timestamp","event","student_id","name","entry_time","exit_time","thumb_path","class_name"])
            w.writerow(row)
        with open(global_path,"a",newline="",encoding="utf-8") as fg:
            wg=csv.writer(fg)
            if write_global_header:
                wg.writerow(["timestamp","event","student_id","name","entry_time","exit_time","thumb_path","class_name"])
            wg.writerow(row)
        root_global_dir = os.path.join("autosave","global")
        os.makedirs(root_global_dir, exist_ok=True)
        root_global_path = os.path.join(root_global_dir,"attendance_log.csv")
        write_root_header = not os.path.exists(root_global_path)
        with open(root_global_path,"a",newline="",encoding="utf-8") as fr:
            wr = csv.writer(fr)
            if write_root_header:
                wr.writerow(["timestamp","event","student_id","name","entry_time","exit_time","thumb_path","class_name"])
            wr.writerow(row)

    # Autosave periodic
    def start_autosave_loop_if_enabled(self):
        if self._autosave_after_id:
            try:
                self.root.after_cancel(self._autosave_after_id)
            except Exception:
                pass
            self._autosave_after_id = None
        if self.autosave_var.get():
            try:
                interval = int(self.autosave_interval.get())
                if interval < 5:
                    interval = 5
            except Exception:
                interval = 60
                self.autosave_interval.set(interval)
            self._autosave_after_id = self.root.after(interval*1000, self._autosave_timer_callback)
        else:
            self._autosave_after_id = None

    def _autosave_timer_callback(self):
        try:
            self.perform_autosave()
        except Exception:
            pass
        self.start_autosave_loop_if_enabled()

    def perform_autosave(self, final=False):
        if (not self.autosave_var.get()) and not final:
            return
        if not self.attendance_rows:
            return
        grouped = {}
        for row in self.attendance_rows:
            class_name = row[7] or "global"
            grouped.setdefault(class_name, []).append(row)
        try:
            for class_name, rows in grouped.items():
                for r in rows:
                    try:
                        ok, res = insert_event_db(r, parent=self.root)
                        if not ok:
                            pass
                    except Exception:
                        pass

            for class_name, rows in grouped.items():
                base_dir = os.path.join("autosave", class_name)
                os.makedirs(base_dir, exist_ok=True)
                today_str = datetime.now().strftime("%Y-%m-%d")
                daily_path = os.path.join(base_dir, f"{today_str}_attendance.csv")
                global_path = os.path.join(base_dir, "attendance_log.csv")
                write_daily_header = not os.path.exists(daily_path)
                write_global_header = not os.path.exists(global_path)
                with open(daily_path,"a",newline="",encoding="utf-8") as fd:
                    w = csv.writer(fd)
                    if write_daily_header:
                        w.writerow(["timestamp","event","student_id","name","entry_time","exit_time","thumb_path","class_name"])
                    for r in rows:
                        w.writerow(r)
                with open(global_path,"a",newline="",encoding="utf-8") as fg:
                    wg = csv.writer(fg)
                    if write_global_header:
                        wg.writerow(["timestamp","event","student_id","name","entry_time","exit_time","thumb_path","class_name"])
                    for r in rows:
                        wg.writerow(r)
            self.attendance_rows = []
            try:
                self.status_label.config(text=f"Status: Autosaved at {datetime.now().strftime('%H:%M:%S')}")
            except Exception:
                pass
        except Exception as e:
            try:
                self.status_label.config(text=f"Status: Autosave failed: {e}")
            except Exception:
                print("Autosave failed:", e)

    # Manual / search / clear / dedupe
    def manual_entry_popup(self):
        win = Toplevel(self.root)
        win.transient(self.root)
        win.grab_set()
        win.title("Add Manual Attendance")
        win.geometry("460x240")
        Label(win, text="Student ID:", font=("Arial", 11)).pack(pady=(10,2))
        e_id = Entry(win, width=40)
        e_id.pack()
        Label(win, text="Name:", font=("Arial", 11)).pack(pady=(8,2))
        e_name = Entry(win, width=40)
        e_name.pack()
        Label(win, text="Timestamp (YYYY-MM-DD HH:MM:SS) optional:", font=("Arial", 9)).pack(pady=(8,2))
        e_ts = Entry(win, width=40)
        e_ts.pack()
        e_ts.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        def on_add():
            sid = e_id.get().strip()
            name = e_name.get().strip()
            ts_text = e_ts.get().strip()
            if not sid or not name:
                messagebox.showerror("Error", "Please enter student id and name.", parent=win)
                return
            try:
                when = datetime.strptime(ts_text, "%Y-%m-%d %H:%M:%S")
            except Exception:
                if messagebox.askyesno("Invalid Timestamp", "Timestamp invalid — use current time instead?", parent=win):
                    when = datetime.now()
                else:
                    return
            win.destroy()
            self._record_event_row("entry", sid, name, when, None, "", self.class_entry.get().strip())
            ok, sid_or_err = insert_session_entry_db(sid, name, when, "", self.class_entry.get().strip(), parent=self.root)
            if not ok:
                print("Manual insert session DB failed:", sid_or_err)

        Button(win, text="Add", command=on_add, width=12).pack(pady=10)
        Button(win, text="Cancel", command=lambda: (win.grab_release(), win.destroy())).pack()

    def search_attendance(self):
        q = self.search_entry.get().strip().lower()
        if not q:
            messagebox.showinfo("Search", "Enter a search term (student id or name or date/time fragment).", parent=self.root)
            return
        content = self.attendance_text.get("1.0", END)
        lines = [ln for ln in content.splitlines() if ln.strip()]
        results = [ln for ln in lines if q in ln.lower()]
        if not results:
            messagebox.showinfo("Search", "No matching entries found.", parent=self.root)
            return
        win = Toplevel(self.root)
        win.title(f"Search results for: {q}")
        win.geometry("700x400")
        txt = Text(win)
        txt.pack(fill=BOTH, expand=1)
        for ln in results:
            txt.insert(END, ln + "\n")
        def export_search():
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], parent=win)
            if not path:
                return
            try:
                with open(path,"w",newline="",encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["timestamp","event","student_id","name","extra"])
                    for ln in results:
                        parts = [p.strip() for p in re.split(r"\s*\|\s*", ln)]
                        if len(parts) >= 4:
                            w.writerow(parts[:4])
                        else:
                            w.writerow([ln])
                messagebox.showinfo("Export", f"Search results exported to:\n{path}", parent=win)
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not write CSV:\n{e}", parent=win)
        Button(win, text="Export Results", command=export_search).pack(pady=6)

    def clear_todays_attendance(self):
        if not messagebox.askyesno("Clear Today's Attendance", "This will delete all attendance records for today from the DB and UI. Continue?", parent=self.root):
            return
        today = date.today()
        conn = get_db_connection(parent=self.root)
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attendance WHERE DATE(timestamp) = %s", (today,))
                deleted = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                content = self.attendance_text.get("1.0", END)
                remaining = []
                for ln in content.splitlines():
                    parts = [p.strip() for p in re.split(r"\s*\|\s*", ln)]
                    if len(parts) >= 1:
                        try:
                            ts = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                            if ts.date() == today:
                                continue
                        except Exception:
                            pass
                    remaining.append(ln)
                self.attendance_text.config(state=NORMAL)
                self.attendance_text.delete("1.0", END)
                for ln in remaining:
                    self.attendance_text.insert(END, ln + "\n")
                self.attendance_text.config(state=DISABLED)
                messagebox.showinfo("Cleared", f"Deleted {deleted} records for {today.isoformat()}", parent=self.root)
                self.status_label.config(text=f"Status: Cleared today's attendance ({deleted} rows)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear today's attendance:\n{e}", parent=self.root)
        else:
            messagebox.showerror("DB Error", "Cannot connect to DB to perform deletion.", parent=self.root)

    def remove_duplicate_db(self):
        if not messagebox.askyesno("Remove Duplicates", "This will remove duplicate attendance_sessions DB rows that have identical student_id and entry_time (keeps earliest id). Continue?", parent=self.root):
            return
        conn = get_db_connection(parent=self.root)
        if not conn:
            messagebox.showerror("DB Error","Cannot connect to DB.", parent=self.root)
            return
        try:
            cursor = conn.cursor()
            sql = """
                DELETE t1 FROM attendance_sessions t1
                INNER JOIN attendance_sessions t2
                  ON t1.student_id = t2.student_id
                 AND t1.entry_time = t2.entry_time
                 AND t1.id > t2.id
            """
            cursor.execute(sql)
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            # UI dedupe
            seen = set()
            lines = [ln for ln in self.attendance_text.get("1.0", END).splitlines() if ln.strip()]
            new_lines = []
            for ln in lines:
                parts = [p.strip() for p in re.split(r"\s*\|\s*", ln)]
                key = None
                if len(parts) >= 3:
                    key = (parts[0], parts[2])
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                new_lines.append(ln)
            self.attendance_text.config(state=NORMAL)
            self.attendance_text.delete("1.0", END)
            for ln in new_lines:
                self.attendance_text.insert(END, ln + "\n")
            self.attendance_text.config(state=DISABLED)
            messagebox.showinfo("Deduplicated", f"Removed {deleted} duplicate rows from DB and cleaned UI.", parent=self.root)
            self.status_label.config(text=f"Status: Removed {deleted} duplicates")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove duplicates:\n{e}", parent=self.root)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")])
        if not path:
            return
        content = self.attendance_text.get("1.0", END).strip()
        if not content:
            messagebox.showinfo("Export", "Attendance log is empty.", parent=self.root)
            return
        lines = [ln for ln in content.splitlines() if ln.strip()]
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["display_timestamp","event_or_tag","student_id","name","extra"])
                for ln in lines:
                    writer.writerow([ln])
            messagebox.showinfo("Export", f"Attendance exported to:\n{path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not write CSV:\n{e}", parent=self.root)

    
    
    def backup_student_table(self, backup_base_path):
        """
        Create two backup files:
          - <backup_base_path>_student_backup.sql  (SHOW CREATE TABLE + INSERTs)
          - <backup_base_path>_student_backup.csv  (CSV export)
        Returns (ok, (sql_path, csv_path, error_message_if_any))
        """
        try:
            conn = get_db_connection(parent=self.root)
            if conn is None:
                return False, (None, None, "DB connection failed")

            cursor = conn.cursor()

            #create table 
            try:
                cursor.execute("SHOW CREATE TABLE student")
                create_row = cursor.fetchone()
                if create_row and len(create_row) >= 2:
                    create_sql = create_row[1]
                else:
                    create_sql = None
            except Exception as e:
                create_sql = None

    
            try:
                cursor.execute("SELECT * FROM student")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
            except Exception as e:
                cursor.close()
                conn.close()
                return False, (None, None, f"Failed to fetch student rows: {e}")

            # write csv
            csv_path = f"{backup_base_path}_student_backup.csv"
            try:
                with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
                    writer = csv.writer(fcsv)
                    writer.writerow(columns)
                    for r in rows:
                        writer.writerow(r)
            except Exception as e:
                cursor.close()
                conn.close()
                return False, (None, None, f"Failed to write CSV backup: {e}")

            
            sql_path = f"{backup_base_path}_student_backup.sql"
            try:
                with open(sql_path, "w", encoding="utf-8") as fsql:
                    fsql.write(f"-- student table backup created at {datetime.now().isoformat()}\n\n")
                    if create_sql:
                        fsql.write(f"DROP TABLE IF EXISTS `student`;\n")
                        fsql.write(create_sql + ";\n\n")
                
                    if rows:
                        col_list = ", ".join(f"`{c}`" for c in columns)
                        for r in rows:
                            vals = []
                            for v in r:
                                if v is None:
                                    vals.append("NULL")
                                elif isinstance(v, (int, float)):
                                    vals.append(str(v))
                                else:
                
                                    s = str(v).replace("'", "''")
                                    vals.append(f"'{s}'")
                            fsql.write(f"INSERT INTO `student` ({col_list}) VALUES ({', '.join(vals)});\n")
            except Exception as e:
                cursor.close()
                conn.close()
                return False, (None, csv_path, f"Failed to write SQL backup: {e}")

            cursor.close()
            conn.close()
            return True, (sql_path, csv_path, None)
        except Exception as e:
            return False, (None, None, str(e))

    # Attendance 
    def compute_attendance_summary(self):
        """
        UI flow:
         - prompt for start date (YYYY-MM-DD) or empty (all time)
         - prompt for end date (YYYY-MM-DD) or empty
         - ask whether to update student table (yes/no)
         - if update: additional confirmation + backup prompt
         - ask for export CSV path
        """
        start_date = simpledialog.askstring("Start Date (optional)", "Enter start date (YYYY-MM-DD) or leave blank for all time:", parent=self.root)
        if start_date:
            start_date = start_date.strip()
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except Exception:
                messagebox.showerror("Invalid date", "Start date must be YYYY-MM-DD or blank.", parent=self.root)
                return
        end_date = simpledialog.askstring("End Date (optional)", "Enter end date (YYYY-MM-DD) or leave blank for all time:", parent=self.root)
        if end_date:
            end_date = end_date.strip()
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except Exception:
                messagebox.showerror("Invalid date", "End date must be YYYY-MM-DD or blank.", parent=self.root)
                return

        update_student = messagebox.askyesno("Update student table?", "Do you want to update the student table with total_days_present and attendance_percent? (Make sure you have DB backup.)", parent=self.root)

        backup_done = False
        backup_paths = (None, None)
        if update_student:
            # extra confirmation
            if not messagebox.askyesno("Confirm update", "You asked to update the student table. The app will create a backup of the student table before modifying it. Continue?", parent=self.root):
                return
    
            base_path = filedialog.asksaveasfilename(defaultextension="", filetypes=[("SQL + CSV backup base","*")], title="Choose backup filename base (no extension)", parent=self.root)
            if not base_path:
                
                if messagebox.askyesno("No backup selected", "No backup selected. Do you want to continue without updating the student table (skip update)?", parent=self.root):
                    update_student = False
                else:
                    return
            else:
                # create backups
                self.status_label.config(text="Status: Creating student table backup...")
                ok, info = self.backup_student_table(base_path)
                if not ok:
                    sqlp, csvp, err = info
                
                    res = messagebox.askyesno("Backup failed", f"Student table backup failed: {err}\n\nDo you want to continue with the update anyway?", parent=self.root)
                    if not res:
                        return
                    else:
                        backup_done = False
                else:
                    sqlp, csvp, _ = info
                    backup_done = True
                    backup_paths = (sqlp, csvp)
                    messagebox.showinfo("Backup created", f"Backup created:\nSQL: {sqlp}\nCSV: {csvp}", parent=self.root)
                    self.status_label.config(text=f"Status: Backup created ({os.path.basename(sqlp)})")

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], parent=self.root)
        if not path:
            return

        try:
            self.status_label.config(text="Status: Computing attendance summary...")
            self._compute_summary_and_export(start_date, end_date, path, update_student)
            messagebox.showinfo("Done", f"Attendance summary exported to:\n{path}", parent=self.root)
            if update_student and backup_done:
                messagebox.showinfo("Update complete", f"Student table updated.\nBackup files:\n{backup_paths[0]}\n{backup_paths[1]}", parent=self.root)
            self.status_label.config(text=f"Status: Summary exported to {path}")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to compute summary:\n{e}", parent=self.root)
            self.status_label.config(text="Status: Summary failed")

    def _compute_summary_and_export(self, start_date, end_date, export_csv_path, update_student):
        """
        Compute per-student days_present (distinct DATE(entry_time)) and total_class_days (distinct calendar days in the range).
        Writes CSV and optionally updates student table columns total_days_present and attendance_percent.
        """
        filters = []
        params = []
        if start_date:
            filters.append("DATE(entry_time) >= %s")
            params.append(start_date)
        if end_date:
            filters.append("DATE(entry_time) <= %s")
            params.append(end_date)
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        conn = get_db_connection(parent=self.root)
        if conn is None:
            raise RuntimeError("DB connection failed")

        cursor = conn.cursor()

        
        
        q_total = f"SELECT COUNT(DISTINCT DATE(entry_time)) FROM attendance_sessions {where_clause}"
        cursor.execute(q_total, params)
        total_class_days = cursor.fetchone()[0] or 0
 
        if filters:
            q_per = "SELECT student_id, COUNT(DISTINCT DATE(entry_time)) FROM attendance_sessions WHERE present = 1 AND " + " AND ".join(filters) + " GROUP BY student_id"
            per_params = list(params)
        else:
            q_per = "SELECT student_id, COUNT(DISTINCT DATE(entry_time)) FROM attendance_sessions WHERE present = 1 GROUP BY student_id"
            per_params = []

        cursor.execute(q_per, per_params)
        rows = cursor.fetchall()
        per_map = {str(r[0]): int(r[1]) for r in rows}

        # fetch students
        cursor.execute("SELECT id, name FROM student")
        students = cursor.fetchall()

        # write CSV
        with open(export_csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["student_id", "name", "days_present", "total_class_days", "attendance_percent"])
            for sid, name in students:
                sid_s = str(sid)
                dp = per_map.get(sid_s, 0)
                pct = round((100.0 * dp / total_class_days), 2) if total_class_days else 0.0
                w.writerow([sid_s, name, dp, total_class_days, pct])

        # optionally update student table
        if update_student:
            # attempt to add columns if missing (best-effort)
            try:
                # MySQL 8+ supports ADD COLUMN IF NOT EXISTS, but older servers may not
                try:
                    cursor.execute("ALTER TABLE student ADD COLUMN IF NOT EXISTS total_days_present INT DEFAULT 0")
                except Exception:
                    cursor.execute("SHOW COLUMNS FROM student LIKE 'total_days_present'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE student ADD COLUMN total_days_present INT DEFAULT 0")
                try:
                    cursor.execute("ALTER TABLE student ADD COLUMN IF NOT EXISTS attendance_percent DECIMAL(5,2) DEFAULT 0.00")
                except Exception:
                    cursor.execute("SHOW COLUMNS FROM student LIKE 'attendance_percent'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE student ADD COLUMN attendance_percent DECIMAL(5,2) DEFAULT 0.00")
            except Exception as e:
                # log and continue; individual updates will still be attempted
                print("Failed to ensure student summary columns exist:", e)

            # perform update per student
            update_q = "UPDATE student SET total_days_present = %s, attendance_percent = %s WHERE id = %s"
            for sid, name in students:
                sid_s = str(sid)
                dp = per_map.get(sid_s, 0)
                pct = round((100.0 * dp / total_class_days), 2) if total_class_days else 0.0
                try:
                    cursor.execute(update_q, (dp, pct, sid))
                except Exception as e:
                    print("Failed to update student", sid, e)
            conn.commit()

        cursor.close()
        conn.close()
 
    def confirm_exit(self, timeout_seconds=5):
        if hasattr(self, "_confirm_win") and getattr(self, "_confirm_win", None) and self._confirm_win.winfo_exists():
            return
        win = Toplevel(self.root)
        self._confirm_win = win
        win.title("Confirm Exit")
        win.transient(self.root)
        win.grab_set()
        win.geometry("380x140")
        win.resizable(False, False)
        Label(win, text="Are you sure you want to exit?", font=("Arial", 12, "bold")).pack(pady=(12,6))
        countdown_lbl = Label(win, text=f"Auto-cancel in {timeout_seconds} s", font=("Arial", 10))
        countdown_lbl.pack()
        btns = Frame(win)
        btns.pack(pady=10)
        def on_yes():
            try:
                self.root.bell()
            except Exception:
                pass
            win.grab_release()
            win.destroy()
            self.exit_fullscreen()
        def on_no():
            win.grab_release()
            win.destroy()
        yes_btn = Button(btns, text="Yes", width=10, command=on_yes)
        yes_btn.grid(row=0, column=0, padx=8)
        no_btn = Button(btns, text="No", width=10, command=on_no)
        no_btn.grid(row=0, column=1, padx=8)
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")
        def countdown(n):
            if not win.winfo_exists():
                return
            if n <= 0:
                try:
                    win.grab_release()
                except Exception:
                    pass
                try:
                    win.destroy()
                except Exception:
                    pass
                return
            countdown_lbl.config(text=f"Auto-cancel in {n} s")
            win.after(1000, lambda: countdown(n-1))
        countdown(timeout_seconds)

    def exit_fullscreen(self):
        try:
            try:
                self.perform_autosave(final=True)
            except Exception:
                pass
            self.root.attributes("-fullscreen", False)
            self.on_close()
        except Exception:
            try:
                self.root.quit()
            except Exception:
                pass

 
if __name__ == "__main__":
    root = Tk()
    app = FullscreenRecognizer(root)
    root.mainloop()
