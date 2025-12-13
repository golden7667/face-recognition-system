
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import mysql.connector
import os
from dotenv import load_dotenv
import cv2
import numpy as np
from datetime import datetime
import re

# load .env if present
load_dotenv()

 
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASS", "golden123")
DB_NAME = os.environ.get("DB_NAME", "facedb")  


def get_pooled_connection(parent=None):
    """Return a MySQL connection or None on error."""
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
            messagebox.showerror("DB Error", f"Could not connect to database:\n{e}", parent=parent)
        else:
            print("DB Error:", e)
        return None

def ensure_attendance_table(parent=None):
    """Create a simple attendance table if it does not exist (best-effort)."""
    conn = get_pooled_connection(parent=parent)
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
    except Exception:
         
        pass
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

    
    conn = get_pooled_connection(parent=parent)
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(64),
                name VARCHAR(255),
                timestamp DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        return True
    except Exception as e:
        if parent:
            messagebox.showerror("DB Error", f"Could not ensure attendance table:\n{e}", parent=parent)
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

def insert_attendance_row(student_id: str, name: str, when: datetime, parent=None):
    """Insert an attendance row using parameterized query (best-effort)."""
    conn = get_pooled_connection(parent=parent)
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO attendance (student_id, name, timestamp) VALUES (%s, %s, %s)"
        cursor.execute(sql, (str(student_id), str(name), when))
        conn.commit()
        return True
    except Exception as e:
        if parent:
            messagebox.showerror("DB Error", f"Failed to insert attendance:\n{e}", parent=parent)
        else:
            print("DB Error inserting attendance:", e)
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


# TRAIN /  
class Train:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x700+50+20")
        self.root.state('zoomed')  
        self.root.title("Train & Recognize - Face System")

        
        top_frame = Frame(self.root, bg="white")
        top_frame.pack(fill=X)
        try:
            img1 = Image.open("image/G2CM_FI454_Learn_Article_Images_[Facial_recognition]_V1a-1.webp").resize((400,80), Image.LANCZOS)
            self.img1 = ImageTk.PhotoImage(img1)
            Label(top_frame, image=self.img1, bg="white").pack(side=LEFT, padx=5, pady=5)
        except Exception:
            pass

        try:
            img2 = Image.open("image/ggggg.jpg.webp").resize((400,80), Image.LANCZOS)
            self.img2 = ImageTk.PhotoImage(img2)
            Label(top_frame, image=self.img2, bg="white").pack(side=LEFT, padx=5, pady=5)
        except Exception:
            pass
        
        try:
            img3 = Image.open("image/Ethical-Hacking.jpg").resize((400,80), Image.LANCZOS)
            self.img3 = ImageTk.PhotoImage(img1)
            Label(top_frame, image=self.img3, bg="white").pack(side=LEFT, padx=5, pady=5)
        except Exception:
            pass
        
        try:
            img4 = Image.open("image/studen.webp").resize((400,80), Image.LANCZOS)
            self.img4 = ImageTk.PhotoImage(img2)
            Label(top_frame, image=self.img4, bg="white").pack(side=LEFT, padx=5, pady=5)
        except Exception:
            pass

        
        ensure_attendance_table(parent=self.root)

        body = Frame(self.root, bg="white")
        body.pack(fill=BOTH, expand=True, padx=20, pady=20)

        title = Label(body, text="FACE DETECTION / RECOGNITION", font=("Arial", 22, "bold"), bg="white", fg="darkgreen")
        title.pack(pady=10)

        instructions = Label(body, text="Put training images in the 'data/' folder.\nFilenames must start with the student id, e.g. 123.jpg or 123_upl.jpg", bg="white")
        instructions.pack(pady=5)

        # Train button
        train_btn = Button(body, text="Train Model", font=("Arial", 14, "bold"), bg="green", fg="white", width=20, command=self.train_model)
        train_btn.pack(pady=12)

        
        recog_btn = Button(body, text="Open Recognizer", font=("Arial", 14, "bold"), bg="blue", fg="white", width=20, command=self.open_recognizer)
        recog_btn.pack(pady=6)

    
        self.status_lbl = Label(body, text="Ready", bg="white", fg="black")
        self.status_lbl.pack(pady=12)

    def open_recognizer(self):
        new_win = Toplevel(self.root)
        Recognizer(new_win)

    def train_model(self):
        """Train LBPH recognizer from images in data/ and save classifier + labels."""
        self.status_lbl.config(text="Training... please wait")
        self.root.update_idletasks()

        data_dir = "data"
        trainer_dir = "trainer"
        os.makedirs(trainer_dir, exist_ok=True)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if face_cascade.empty():
            messagebox.showerror("Error", "Could not load Haar cascade. Check your OpenCV installation.", parent=self.root)
            self.status_lbl.config(text="Failed: cascade not loaded")
            return

        if not os.path.isdir(data_dir):
            messagebox.showerror("Error", f"Data directory not found: {data_dir}\nCreate it and add face images.", parent=self.root)
            self.status_lbl.config(text="No data folder")
            return

        files = [f for f in os.listdir(data_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not files:
            messagebox.showerror("Error", f"No images found in {data_dir}. Add photos and try again.", parent=self.root)
            self.status_lbl.config(text="No images")
            return

        faces = []
        labels = []
        sid_to_label = {}
        next_label = 0

        for fname in files:
            path = os.path.join(data_dir, fname)

            
            base = os.path.basename(fname)
            sid = re.split(r"[_\.]", base)[0].strip()
            if sid == "":
                print(f"Skipping {path}: cannot extract sid")
                continue

            if sid not in sid_to_label:
                sid_to_label[sid] = next_label
                next_label += 1
            label_int = sid_to_label[sid]

            img = cv2.imread(path)
            if img is None:
                print(f"Skipping unreadable image: {path}")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50,50))
            if len(rects) == 0:
                print(f"No face found in {path} - skipping")
                continue

            # pick largest face
            rects = sorted(rects, key=lambda r: r[2]*r[3], reverse=True)
            x,y,w,h = rects[0]
            face_roi = gray[y:y+h, x:x+w]
            try:
                face_resized = cv2.resize(face_roi, (200,200))
            except Exception:
                face_resized = face_roi

            faces.append(face_resized)
            labels.append(label_int)

        if len(faces) == 0:
            messagebox.showerror("Error", "No faces found in dataset. Add clearer face images and try again.", parent=self.root)
            self.status_lbl.config(text="No faces found")
            return

        # Train recognizer
        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            messagebox.showerror("Error", "cv2.face.LBPHFaceRecognizer_create not available. Install opencv-contrib-python.", parent=self.root)
            self.status_lbl.config(text="cv2.face missing")
            return

        try:
            recognizer.train(faces, np.array(labels))
        except Exception as e:
            messagebox.showerror("Training Error", f"Training failed: {e}", parent=self.root)
            self.status_lbl.config(text="Training failed")
            return

        # Save model
        model_path = os.path.join(trainer_dir, "classifier.xml")
        try:
            recognizer.write(model_path)
        except Exception:
            recognizer.save(model_path)

        # Save label
        labels_path = os.path.join(trainer_dir, "labels.txt")
        try:
            # invert m
            with open(labels_path, "w", encoding="utf-8") as f:
                for sid, lbl in sid_to_label.items():
                    f.write(f"{lbl},{sid}\n")
        except Exception as e:
            messagebox.showwarning("Warning", f"Model saved but failed to write labels file: {e}", parent=self.root)
            self.status_lbl.config(text="Saved model, labels write failed")
            return

        messagebox.showinfo("Success", f"Training complete.\nModel: {model_path}\nLabels: {labels_path}", parent=self.root)
        self.status_lbl.config(text="Training complete")

class Recognizer:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1000x600+100+50")
        self.root.title("Face Recognition")

        title_lbl = Label(self.root, text="FACE RECOGNITION", font=("Arial", 24, "bold"), bg="white", fg="darkgreen")
        title_lbl.pack(side=TOP, fill=X)

        main_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        info_lbl = Label(main_frame, text="Click Start to open webcam. Press 'q' in the video window to quit.", bg="white")
        info_lbl.pack(pady=8)

        start_btn = Button(main_frame, text="Start Recognition", font=("Arial", 14, "bold"), bg="blue", fg="white", command=self.start_recognition)
        start_btn.pack(pady=10)

        self.result_label = Label(main_frame, text="Waiting...", font=("Arial", 14), bg="white", fg="blue")
        self.result_label.pack(pady=10)

    def load_label_map(self):
        labels_path = os.path.join("trainer", "labels.txt")
        if not os.path.exists(labels_path):
            messagebox.showerror("Error", f"Labels file not found:\n{labels_path}\nTrain data first.", parent=self.root)
            return None
        label_to_sid = {}
        try:
            with open(labels_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",", 1)
                    if len(parts) != 2:
                        continue
                    label_int = int(parts[0])
                    sid = parts[1]
                    label_to_sid[label_int] = sid
        except Exception as e:
            messagebox.showerror("Error", f"Could not read labels file:\n{e}", parent=self.root)
            return None
        return label_to_sid

    def load_student_names(self):
        conn = get_pooled_connection(parent=self.root)
        if conn is None:
            return None
        sid_to_name = {}
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT `id`, `name` FROM `student`")
            rows = cursor.fetchall()
            for sid, name in rows:
                sid_to_name[str(sid)] = name
        except Exception as e:
            messagebox.showerror("Error", f"Could not load student names:\n{e}", parent=self.root)
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
        return sid_to_name

    def start_recognition(self):
        model_path = os.path.join("trainer", "classifier.xml")
        if not os.path.exists(model_path):
            messagebox.showerror("Error", f"Model file not found:\n{model_path}\nTrain data first.", parent=self.root)
            return

        label_map = self.load_label_map()
        if label_map is None:
            return

        sid_to_name = self.load_student_names()
        if sid_to_name is None:
            return

    
        print("Loaded label_map (label -> sid):", label_map)
        print("Loaded sid_to_name (sid -> name):", sid_to_name)

        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(model_path)
        except AttributeError:
            messagebox.showerror("Error", "cv2.face.LBPHFaceRecognizer_create not available. Install opencv-contrib-python.", parent=self.root)
            return
        except Exception as e:
            messagebox.showerror("Error loading model", f"{e}", parent=self.root)
            return

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if face_cascade.empty():
            messagebox.showerror("Error", "Could not load Haar cascade.", parent=self.root)
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Cannot open webcam.", parent=self.root)
            return

        messagebox.showinfo("Info", "Webcam started. Press 'q' in the video window to quit.", parent=self.root)

    
        CONFIDENCE_THRESHOLD = 60.0

        
        DEBUG_PREDICTIONS = False

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50,50))

            
                detected_text = "No face detected"

                for (x, y, w, h) in faces:
                    roi_gray = gray[y:y+h, x:x+w]
                    try:
                        roi_gray_resized = cv2.resize(roi_gray, (200, 200))
                    except Exception:
                        roi_gray_resized = roi_gray

                    try:
                        label_int, confidence = recognizer.predict(roi_gray_resized)
                    except Exception as e:
            
                        label_int, confidence = -1, float('inf')

    
                    if DEBUG_PREDICTIONS:
                        print(f"Predicted label={label_int}, confidence={confidence}")

                    if confidence <= CONFIDENCE_THRESHOLD and label_int in label_map:
                        sid = label_map[label_int]          
                        name = sid_to_name.get(str(sid), "Unknown")
                        
                        pct = max(0, min(100, round(100 - confidence)))
                        detected_text = f"ID: {sid}, Name: {name}  (score: {pct})"
                        color = (0, 255, 0)

                        # Log 
                        try:
                            insert_attendance_row(sid, name, datetime.now(), parent=self.root)
                        except Exception:
                            pass
                    else:
                    
                        detected_text = f"Unknown (conf={round(confidence,1)})"
                        color = (0, 0, 255)

                    
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(frame, detected_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                
                self.result_label.config(text=detected_text)

                cv2.imshow("Face Recognition - press 'q' to quit", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.result_label.config(text="Recognition stopped.")
 
 
if __name__ == "__main__":
    root = Tk()
    app = Train(root)
    root.mainloop()
