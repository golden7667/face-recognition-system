from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import csv
import re
import traceback
from datetime import datetime, date, timedelta
import mysql.connector
import uuid
import threading
import time
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import subprocess

# matplotlib for graphs
import matplotlib
matplotlib.use("Agg")   
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

 
try:
    import cv2
except Exception:
    cv2 = None
 
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "golden1234"
DB_NAME = "facedb"

 
SCHED_CONFIG_FILE = "backup_scheduler_config.json"
 
def get_db_connection(parent=None, database=None):
    """Return a MySQL connection (optionally to `database`)."""
    try:
        conn_args = dict(host=DB_HOST, user=DB_USER, password=DB_PASS, buffered=True)
        if database:
            conn_args['database'] = database
        conn = mysql.connector.connect(**conn_args)
        return conn
    except mysql.connector.Error as err:
        if parent:
            try:
                messagebox.showerror("MySQL Connection Error", f"Could not connect to MySQL:\n{err}", parent=parent)
            except Exception:
                pass
        else:
            print(f"MySQL Connection Error: {err}")
        return None

def ensure_core_tables(conn):
    """Create student/attendance_sessions/attendance tables if missing on given connection."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255),
            misc TEXT,
            total_days_present INT DEFAULT 0,
            attendance_percent DECIMAL(5,2) DEFAULT 0.0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            student_id VARCHAR(255),
            name VARCHAR(255),
            entry_time DATETIME,
            exit_time DATETIME,
            class_name VARCHAR(255),
            present TINYINT DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INT PRIMARY KEY AUTO_INCREMENT,
            timestamp DATETIME,
            event VARCHAR(50),
            student_id VARCHAR(255),
            name VARCHAR(255),
            entry_time DATETIME,
            exit_time DATETIME,
            thumb_path TEXT,
            class_name VARCHAR(255)
        )
    """)
    conn.commit()
    cur.close()

def get_db_connection_and_ensure(parent=None):
    """Get connection to DB_NAME and ensure core tables exist."""
    conn = get_db_connection(parent=parent, database=DB_NAME)
    if conn is None:
        return None
    try:
        ensure_core_tables(conn)
    except Exception:
        pass
    return conn

 
def backup_student_table_to_paths(backup_base_path, parent=None, use_mysqldump=False, use_show_create=False):
    """
    Create SQL + CSV backups of student table and return (ok, (sql_path, csv_path, error_msg_or_none))
    """
    csv_path = f"{backup_base_path}_student_backup.csv"
    sql_path = f"{backup_base_path}_student_backup.sql"

     
    if use_mysqldump:
        try:
            cmd = [
                "mysqldump",
                "-h", DB_HOST,
                "-u", DB_USER,
                f"-p{DB_PASS}",
                DB_NAME,
                "student"
            ]
            with open(sql_path, "wb") as fout:
                proc = subprocess.Popen(cmd, stdout=fout, stderr=subprocess.PIPE)
                _, stderr = proc.communicate()
                rc = proc.returncode
            if rc != 0:
                serr = stderr.decode(errors='ignore') if stderr else "mysqldump failed"
                return False, (None, None, f"mysqldump failed (returncode={rc}): {serr}")
        except FileNotFoundError:
            return False, (None, None, "mysqldump not found on PATH")
        except Exception as e:
            return False, (None, None, f"mysqldump error: {e}")

  
    conn = get_db_connection_and_ensure(parent=parent)
    if conn is None:
        return False, (None, None, "DB connection failed")
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM student")
        rows = cur.fetchall()
        if rows:
            columns = list(rows[0].keys())
        else:
            columns = ["id", "name", "misc", "total_days_present", "attendance_percent"]
    except Exception as e:
        cur.close()
        conn.close()
        return False, (None, None, f"Failed to fetch student rows: {e}")

    # Write CSV
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow(columns)
            for r in rows:
                writer.writerow([r.get(c) for c in columns])
    except Exception as e:
        cur.close()
        conn.close()
        return False, (None, None, f"Failed to write CSV backup: {e}")

    
    if use_mysqldump:
        cur.close()
        conn.close()
        return True, (sql_path, csv_path, None)

    # Otherwise 
    try:
        with open(sql_path, "w", encoding="utf-8") as fsql:
            fsql.write(f"-- student table backup created at {datetime.now().isoformat()}\n\n")
            fsql.write("DROP TABLE IF EXISTS student;\n")
            create_stmt = None
            if use_show_create:
                try:
                    cur2 = conn.cursor()
                    cur2.execute("SHOW CREATE TABLE student")
                    row = cur2.fetchone()
                    if row and len(row) > 1:
                        create_stmt = row[1] + ";\n"
                    cur2.close()
                except Exception:
                    create_stmt = None
            if create_stmt:
                fsql.write(create_stmt + "\n")
            else:
                fsql.write("""
CREATE TABLE student (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255),
  misc TEXT,
  total_days_present INT DEFAULT 0,
  attendance_percent DECIMAL(5,2) DEFAULT 0.0
);
\n""")
            if rows:
                col_list = ", ".join(f"`{c}`" for c in columns)
                for r in rows:
                    vals = []
                    for c in columns:
                        v = r.get(c)
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            s = str(v).replace("'", "\\'")
                            vals.append(f"'{s}'")
                    fsql.write(f"INSERT INTO student ({col_list}) VALUES ({', '.join(vals)});\n")
    except Exception as e:
        cur.close()
        conn.close()
        return False, (None, csv_path, f"Failed to write SQL backup: {e}")

    cur.close()
    conn.close()
    return True, (sql_path, csv_path, None)

# Safe Test-Restore to Temp Schema  
def test_restore_student_table(sql_path, parent=None, allow_cleanup=True):
    """
    Run the provided SQL into a temporary schema and validate that a 'student' table is created.
    """
    if not os.path.exists(sql_path):
        return False, "SQL file not found", {}

    try:
        sql_text = open(sql_path, "r", encoding="utf-8").read()
    except Exception as e:
        return False, f"Could not read SQL file: {e}", {}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_db = f"{DB_NAME}_test_restore_{ts}"

    try:
        admin_conn = get_db_connection(parent=parent, database=None)
        if admin_conn is None:
            return False, "Could not connect to MySQL server for test-restore", {}
        admin_cursor = admin_conn.cursor()
    except Exception as e:
        return False, f"Could not connect to MySQL server for test-restore: {e}", {}

    try:
        admin_cursor.execute(f"CREATE DATABASE `{temp_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        admin_conn.commit()
    except mysql.connector.Error as err:
        try:
            admin_conn.rollback()
        except Exception:
            pass
        admin_cursor.close()
        admin_conn.close()
        return False, f"Failed to create temporary schema `{temp_db}`: {err}", {}

    temp_conn = None
    temp_cursor = None
    try:
        temp_conn = get_db_connection(parent=parent, database=temp_db)
        if temp_conn is None:
            raise RuntimeError("Failed to connect to temporary schema after creation")
        temp_cursor = temp_conn.cursor()
        for result in temp_cursor.execute(sql_text, multi=True):
            pass
        temp_conn.commit()

        temp_cursor.execute("SHOW TABLES LIKE 'student'")
        tbl = temp_cursor.fetchone()
        if not tbl:
            if temp_cursor:
                try:
                    temp_cursor.close()
                except Exception:
                    pass
            if temp_conn:
                try:
                    temp_conn.close()
                except Exception:
                    pass
            if allow_cleanup:
                try:
                    admin_cursor.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
                    admin_conn.commit()
                except Exception:
                    pass
            admin_cursor.close()
            admin_conn.close()
            return False, "SQL executed but `student` table not found in temp schema.", {"temp_db": temp_db, "student_exists": False, "student_row_count": 0}

        try:
            temp_cursor.execute("SELECT COUNT(*) FROM student")
            cnt = temp_cursor.fetchone()[0] or 0
        except Exception:
            cnt = -1

        try:
            temp_cursor.close()
        except Exception:
            pass
        try:
            temp_conn.close()
        except Exception:
            pass

        if allow_cleanup:
            try:
                admin_cursor.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
                admin_conn.commit()
            except Exception:
                pass

        admin_cursor.close()
        admin_conn.close()
        return True, "Test-restore succeeded. `student` table found in temp schema.", {"temp_db": temp_db, "student_exists": True, "student_row_count": cnt}
    except mysql.connector.Error as err:
        try:
            if temp_conn:
                temp_conn.rollback()
                temp_conn.close()
        except Exception:
            pass
        try:
            admin_cursor.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
            admin_conn.commit()
        except Exception:
            pass
        admin_cursor.close()
        admin_conn.close()
        return False, f"MySQL error while executing SQL in temp schema: {err}", {"temp_db": temp_db}
    except Exception as e:
        try:
            if temp_conn:
                temp_conn.close()
        except Exception:
            pass
        try:
            admin_cursor.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
            admin_conn.commit()
        except Exception:
            pass
        admin_cursor.close()
        admin_conn.close()
        return False, f"Unexpected error during test-restore: {e}", {"temp_db": temp_db}
# Schema 
def compare_live_student_with_sql_backup(sql_path, parent=None, sample_rows=10):
    ok, msg, info = test_restore_student_table(sql_path, parent=parent, allow_cleanup=False)
    if not ok:
        return False, f"Test-restore failed: {msg}", info

    temp_db = info.get("temp_db")
    details = {"temp_db": temp_db}

    live_conn = get_db_connection(parent=parent, database=DB_NAME)
    temp_conn = get_db_connection(parent=parent, database=temp_db)
    if live_conn is None or temp_conn is None:
        try:
            admin = get_db_connection(parent=parent, database=None)
            if admin:
                cur = admin.cursor()
                cur.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
                admin.commit()
                cur.close()
                admin.close()
        except Exception:
            pass
        return False, "Could not connect to live or temp DB for comparison", {"temp_db": temp_db}

    try:
        live_cur = live_conn.cursor(dictionary=True)
        temp_cur = temp_conn.cursor(dictionary=True)

        live_cur.execute("SHOW COLUMNS FROM student")
        live_columns = [row['Field'] for row in live_cur.fetchall()]
        temp_cur.execute("SHOW COLUMNS FROM student")
        backup_columns = [row['Field'] for row in temp_cur.fetchall()]
        details['live_columns'] = live_columns
        details['backup_columns'] = backup_columns

        live_cur.execute("SELECT COUNT(*) AS c FROM student")
        live_count = int(live_cur.fetchone()['c'] or 0)
        temp_cur.execute("SELECT COUNT(*) AS c FROM student")
        backup_count = int(temp_cur.fetchone()['c'] or 0)
        details['live_row_count'] = live_count
        details['backup_row_count'] = backup_count

        live_cur.execute("SELECT id FROM student ORDER BY id LIMIT %s", (sample_rows,))
        live_ids = [r['id'] for r in live_cur.fetchall()]
        temp_cur.execute("SELECT id FROM student ORDER BY id LIMIT %s", (sample_rows,))
        temp_ids = [r['id'] for r in temp_cur.fetchall()]
        union_ids = sorted(set(live_ids + temp_ids))[:sample_rows]

        sample_diffs = []
        for _id in union_ids:
            live_cur.execute("SELECT * FROM student WHERE id = %s", (_id,))
            lrow = live_cur.fetchone()
            temp_cur.execute("SELECT * FROM student WHERE id = %s", (_id,))
            trow = temp_cur.fetchone()
            if lrow != trow:
                sample_diffs.append({"id": _id, "live_row": dict(lrow) if lrow else None, "backup_row": dict(trow) if trow else None})
        details['sample_diffs'] = sample_diffs

        live_cur.close()
        temp_cur.close()
        live_conn.close()

        admin_conn = get_db_connection(parent=parent, database=None)
        if admin_conn:
            admin_cur = admin_conn.cursor()
            try:
                admin_cur.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
                admin_conn.commit()
            except Exception:
                pass
            admin_cur.close()
            admin_conn.close()

        return True, "Comparison complete", details
    except Exception as e:
        try:
            if live_conn:
                live_conn.close()
            if temp_conn:
                temp_conn.close()
            admin = get_db_connection(parent=parent, database=None)
            if admin:
                cur = admin.cursor()
                cur.execute(f"DROP DATABASE IF EXISTS `{temp_db}`;")
                admin.commit()
                cur.close()
                admin.close()
        except Exception:
            pass
        return False, f"Error during comparison: {e}", {"temp_db": temp_db}

# Nightly  

class NightlyBackupScheduler:
    def __init__(self, parent, enabled=False, time_hhmm="03:00", folder="backups"):
        self.parent = parent
        self.enabled = enabled
        self.time_hhmm = time_hhmm
        self.folder = folder
        self._stop_event = threading.Event()
        self._thread = None

    def load_config(self):
        if os.path.exists(SCHED_CONFIG_FILE):
            try:
                with open(SCHED_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.enabled = cfg.get("enabled", self.enabled)
                    self.time_hhmm = cfg.get("time_hhmm", self.time_hhmm)
                    self.folder = cfg.get("folder", self.folder)
            except Exception:
                pass

    def save_config(self):
        cfg = {"enabled": self.enabled, "time_hhmm": self.time_hhmm, "folder": self.folder}
        try:
            with open(SCHED_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def start(self):
        self.load_config()
        self._stop_event.clear()
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def next_run_seconds(self):
        try:
            hh, mm = [int(p) for p in self.time_hhmm.split(":")]
        except Exception:
            hh, mm = 3, 0
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        delta = (target - now).total_seconds()
        return max(1, int(delta))

    def _run_loop(self):
        while not self._stop_event.is_set():
            if not self.enabled:
                time.sleep(5)
                continue
            sec = self.next_run_seconds()
            while sec > 0 and not self._stop_event.is_set():
                to_sleep = min(60, sec)
                time.sleep(to_sleep)
                sec -= to_sleep
            if self._stop_event.is_set():
                break
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                os.makedirs(self.folder, exist_ok=True)
                base = os.path.join(self.folder, f"{timestamp}")
                if hasattr(self.parent, "backup_student_table"):
                    ok, info = self.parent.backup_student_table(base)
                else:
                    ok, info = backup_student_table_to_paths(base, parent=self.parent)
                if ok:
                    sqlp, csvp, _ = info
                    try:
                        self.parent.status_label.config(text=f"Nightly backup created: {os.path.basename(sqlp)}")
                    except Exception:
                        pass
                else:
                    try:
                        self.parent.status_label.config(text=f"Nightly backup failed: {info[2] if info else 'error'}")
                    except Exception:
                        pass
            except Exception as e:
                try:
                    self.parent.status_label.config(text=f"Nightly backup exception: {e}")
                except Exception:
                    pass

# Main Attendance GUI 
class Attendance:
    def __init__(self, root):
        self.root = root
        self.root.title("Attendance (MySQL)")
        self.root.geometry("1200x720")

        title_lbl = Label(self.root, text="Attendance system (MySQL)",
                          font=("Arial", 22, "bold"), fg="white", bg="#222")
        title_lbl.pack(fill=X)

        main = Frame(self.root)
        main.pack(fill=BOTH, expand=True, padx=8, pady=8)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.columnconfigure(2, weight=0)

        left = Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8))

        frm_inputs = LabelFrame(left, text="Filters", padx=6, pady=6)
        frm_inputs.pack(fill=X, pady=(0,8))
        Label(frm_inputs, text="Class:").grid(row=0, column=0, sticky=W, padx=(0,6))
        self.class_entry = Entry(frm_inputs)
        self.class_entry.grid(row=0, column=1, sticky="ew")
        frm_inputs.columnconfigure(1, weight=1)
        Label(frm_inputs, text="Search:").grid(row=1, column=0, sticky=W, padx=(0,6), pady=(6,0))
        self.search_entry = Entry(frm_inputs)
        self.search_entry.grid(row=1, column=1, sticky="ew", pady=(6,0))

        btn_frame = LabelFrame(left, text="Actions", padx=6, pady=6)
        btn_frame.pack(fill=X, pady=(0,8))
        action_buttons = [
            ("Manual Entry", self.manual_entry_popup),
            ("Search", self.search_attendance),
            ("Export CSV", self.export_csv),
            ("Export PDF", self.export_attendance_pdf),   # PDF export
            ("Clear Today", self.clear_todays_attendance),
            ("Remove Duplicates", self.remove_duplicate_db),
            ("Compute Summary", self.compute_attendance_summary),
            ("Simulate Entry", self.simulate_entry),
            ("Show Graph", self.show_attendance_graph),
        ]
        for idx, (label_text, cmd) in enumerate(action_buttons):
            r = idx // 2
            c = idx % 2
            Button(btn_frame, text=label_text, width=18, command=cmd).grid(row=r, column=c, pady=4, padx=4)

        opts_frame = LabelFrame(left, text="Options", padx=6, pady=6)
        opts_frame.pack(fill=X, pady=(0,8))
        self.autosave_var = BooleanVar(value=True)
        self.autosave_chk = Checkbutton(opts_frame, text="Autosave", variable=self.autosave_var,
                                        command=self.start_autosave_loop_if_enabled)
        self.autosave_chk.grid(row=0, column=0, sticky=W)
        Label(opts_frame, text="Interval(s):").grid(row=0, column=1, sticky=E, padx=(6,2))
        self.autosave_interval = StringVar(value="15")
        self.autosave_interval_entry = Entry(opts_frame, textvariable=self.autosave_interval, width=6)
        self.autosave_interval_entry.grid(row=0, column=2, sticky=E)
        self.auto_update_percent = BooleanVar(value=True)
        self.auto_update_chk = Checkbutton(opts_frame, text="Auto-update %", variable=self.auto_update_percent)
        self.auto_update_chk.grid(row=1, column=0, sticky=W, pady=(6,0))

        center = Frame(main)
        center.grid(row=0, column=1, sticky="nsew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        self.attendance_text = Text(center, state=DISABLED, wrap=NONE)
        self.attendance_text.grid(row=0, column=0, sticky="nsew")
        v_scroll = ttk.Scrollbar(center, orient=VERTICAL, command=self.attendance_text.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(center, orient=HORIZONTAL, command=self.attendance_text.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.attendance_text['yscrollcommand'] = v_scroll.set
        self.attendance_text['xscrollcommand'] = h_scroll.set

        right = Frame(main)
        right.grid(row=0, column=2, sticky="nsew", padx=(8,0))

        thumb_frame = LabelFrame(right, text="Recent Faces", padx=6, pady=6)
        thumb_frame.pack(fill=X)
        self.max_thumbs = 6
        self.thumbnail_images = []
        self.thumb_labels = []
        for r in range(3):
            for c in range(2):
                lbl = Label(thumb_frame, width=80, height=80, bg="#eee", bd=1, relief=SOLID)
                lbl.grid(row=r, column=c, padx=4, pady=4)
                self.thumb_labels.append(lbl)

        backup_frame = LabelFrame(right, text="Backup / Restore", padx=6, pady=6)
        backup_frame.pack(fill=X, pady=(8,6))
        Button(backup_frame, text="Backup Student Table", width=22, command=self.ui_backup_student_table).pack(pady=4)
        Button(backup_frame, text="Restore Student Table", width=22, command=self.ui_restore_student_table).pack(pady=4)
        Button(backup_frame, text="Test Restore (Safe)", width=22, command=self.ui_test_restore_student_table).pack(pady=4)
        Button(backup_frame, text="Compare with Backup", width=22, command=self.ui_compare_with_backup).pack(pady=4)

        flags_frame = Frame(right)
        flags_frame.pack(fill=X, pady=(4,8))
        self.use_mysqldump_var = BooleanVar(value=False)
        self.use_showcreate_var = BooleanVar(value=True)
        Checkbutton(flags_frame, text="Use mysqldump", variable=self.use_mysqldump_var).pack(anchor=W)
        Checkbutton(flags_frame, text="Prefer SHOW CREATE", variable=self.use_showcreate_var).pack(anchor=W)

        sched_frame = LabelFrame(right, text="Nightly Backup", padx=6, pady=6)
        sched_frame.pack(fill=X)
        Label(sched_frame, text="Time (HH:MM)").grid(row=0, column=0, sticky=W)
        self.schedule_time_var = StringVar(value="03:00")
        self.schedule_time_entry = Entry(sched_frame, width=6, textvariable=self.schedule_time_var)
        self.schedule_time_entry.grid(row=0, column=1, sticky=E, padx=(6,0))
        Label(sched_frame, text="Folder:").grid(row=1, column=0, sticky=W, pady=(6,0))
        self.schedule_folder_var = StringVar(value="backups")
        self.schedule_folder_entry = Entry(sched_frame, width=20, textvariable=self.schedule_folder_var)
        self.schedule_folder_entry.grid(row=1, column=1, sticky=E, pady=(6,0))
        Button(sched_frame, text="Choose...", command=self.choose_backup_folder).grid(row=1, column=2, padx=(6,0))
        self.schedule_enabled_var = BooleanVar(value=False)
        self.schedule_chk = Checkbutton(sched_frame, text="Enable nightly", variable=self.schedule_enabled_var, command=self.toggle_scheduler)
        self.schedule_chk.grid(row=2, column=0, columnspan=2, sticky=W, pady=(8,0))
        Button(sched_frame, text="Backup Now", command=self.manual_backup_now).grid(row=3, column=0, columnspan=3, pady=(8,0))

        status_bar = Frame(self.root, bd=1, relief=SUNKEN)
        status_bar.pack(fill=X, side=BOTTOM)
        self.status_label = Label(status_bar, text="Status: Ready", anchor=W)
        self.status_label.pack(fill=X)

        self.attendance_rows = []
        self._autosave_after_id = None

        self.scheduler = NightlyBackupScheduler(self,
                                                enabled=False,
                                                time_hhmm=self.schedule_time_var.get(),
                                                folder=self.schedule_folder_var.get())
        self.scheduler.load_config()
        self.schedule_time_var.set(self.scheduler.time_hhmm)
        self.schedule_folder_var.set(self.scheduler.folder)
        self.schedule_enabled_var.set(self.scheduler.enabled)
        if self.scheduler.enabled:
            self.scheduler.start()

        self.start_autosave_loop_if_enabled()

    # PDF Export  
    def export_attendance_pdf(self):
        """
        Enhanced PDF exporter:
         - allows choosing source: 'display' (Text widget) or 'db' (attendance table)
         - optional embedding of thumbnails (if thumb_path exists and file is available)
         - renders a neat table in the PDF
        """
        choice = simpledialog.askstring("Export PDF - Source", "Enter source to export ('display' or 'db'):", initialvalue="display", parent=self.root)
        if not choice:
            return
        choice = choice.strip().lower()
        include_thumbs = messagebox.askyesno("Include thumbnails?", "Include thumbnails in the PDF if available?", parent=self.root)

        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF files", "*.pdf")],
                                            title="Save attendance as PDF",
                                            parent=self.root)
        if not path:
            return

        try:
            doc = SimpleDocTemplate(path, leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
            styles = getSampleStyleSheet()
            normal = styles["Normal"]
            normal.fontName = "Helvetica"
            normal.fontSize = 9
            normal.leading = 11

            flowables = []
            title_style = styles.get("Title", normal)
            flowables.append(Paragraph("Attendance Export", title_style))
            flowables.append(Paragraph(f"Export time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal))
            flowables.append(Paragraph("<br/>", normal))

            # Build table data
            table_data = []
            if choice == "db":
                
                conn = get_db_connection(parent=self.root, database=DB_NAME)
                if conn is None:
                    messagebox.showerror("DB Error", "Cannot connect to DB for export.", parent=self.root)
                    return
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT timestamp, event, student_id, name, entry_time, exit_time, thumb_path, class_name FROM attendance ORDER BY timestamp")
                rows = cur.fetchall()
                cur.close()
                conn.close()
                header = ["timestamp", "event", "student_id", "name", "entry_time", "exit_time", "class_name"]
                if include_thumbs:
                    header = ["thumb", *header]
                table_data.append(header)
                for r in rows:
                    row_cells = []
                    if include_thumbs:
                        tp = r.get("thumb_path") or ""
                        row_cells.append(tp)   
                    row_cells.extend([
                        r.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if isinstance(r.get("timestamp"), datetime) else str(r.get("timestamp") or ""),
                        str(r.get("event") or ""),
                        str(r.get("student_id") or ""),
                        str(r.get("name") or ""),
                        r.get("entry_time").strftime("%Y-%m-%d %H:%M:%S") if isinstance(r.get("entry_time"), datetime) else str(r.get("entry_time") or ""),
                        r.get("exit_time").strftime("%Y-%m-%d %H:%M:%S") if isinstance(r.get("exit_time"), datetime) else str(r.get("exit_time") or ""),
                        str(r.get("class_name") or ""),
                    ])
                    table_data.append(row_cells)
            else:
                
                content = self.attendance_text.get("1.0", END).strip()
                if not content:
                    messagebox.showinfo("Export PDF", "Attendance log is empty.", parent=self.root)
                    return
                lines = [ln for ln in content.splitlines() if ln.strip()]
                header = ["timestamp", "event_or_tag", "student_id", "name", "extra"]
                if include_thumbs:
                    header = ["thumb", *header]
                table_data.append(header)
                for ln in lines:
                    parts = [p.strip() for p in re.split(r"\s*\|\s*", ln)]
                    
                    if len(parts) >= 5:
                        main_parts = parts[:5]
                    else:
                        main_parts = parts + [""] * (5 - len(parts))
                    row_cells = []
                     
                    thumb_guess = ""
                    if include_thumbs:
                         
                        thumb_guess = ""
                        row_cells.append(thumb_guess)
                    row_cells.extend(main_parts)
                    table_data.append(row_cells)

             
            processed_table = []
            max_rows_for_images = 500  
            for idx_row, row in enumerate(table_data):
                if idx_row == 0:
                    
                    processed_table.append([Paragraph(str(c), styles["Heading5"]) for c in row])
                    continue
                proc_row = []
                for col_idx, cell in enumerate(row):
                    
                    if include_thumbs and col_idx == 0:
                        tp = cell or ""
                        if tp and os.path.exists(tp) and idx_row <= max_rows_for_images:
                            try:
                                # scale to fit a small box
                                rlimg = RLImage(tp, width=48, height=48)
                                proc_row.append(rlimg)
                            except Exception:
                                proc_row.append(Paragraph(os.path.basename(tp), normal))
                        else:
                            proc_row.append(Paragraph("", normal))
                    else:
                        proc_row.append(Paragraph(str(cell or ""), normal))
                processed_table.append(proc_row)
 
            ncols = len(processed_table[0]) if processed_table else 1
            page_width = 540   
            if include_thumbs:
                
                thumb_col = 50
                other_width = max(60, int((page_width - thumb_col) / max(1, ncols - 1)))
                col_widths = [thumb_col] + [other_width] * (ncols - 1)
            else:
                col_widths = [int(page_width / ncols)] * ncols

            tbl = Table(processed_table, colWidths=col_widths, repeatRows=1)
            tbl_style = TableStyle([
                ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("ALIGN", (0,0), (-1,0), "CENTER"),
                ("LEFTPADDING", (0,0), (-1,-1), 4),
                ("RIGHTPADDING", (0,0), (-1,-1), 4),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ])
            tbl.setStyle(tbl_style)
            flowables.append(tbl)

            doc.build(flowables)
            messagebox.showinfo("Export PDF", f"PDF created:\n{path}", parent=self.root)
            self.status_label.config(text=f"Status: PDF exported ({os.path.basename(path)})")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Export PDF Error", f"Failed to create PDF:\n{e}", parent=self.root)
            self.status_label.config(text="Status: PDF export failed")

    # Thumbnail 
    def _save_thumbnail_for_sid(self, face_bgr, sid):
        try:
            os.makedirs("autosave/thumbs", exist_ok=True)
            class_name = (self.class_entry.get().strip() or "global")
            folder = os.path.join("autosave", "thumbs", class_name)
            os.makedirs(folder, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"{ts}_{sid}.jpg"
            path = os.path.join(folder, fname)
            try:
                if cv2 is not None and hasattr(cv2, "cvtColor") and hasattr(face_bgr, "shape"):
                    face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
                    pil = Image.fromarray(face_rgb)
                    pil = pil.resize((200, 200), Image.LANCZOS)
                    pil.save(path, quality=85)
                else:
                    if isinstance(face_bgr, Image.Image):
                        pil = face_bgr.resize((200, 200), Image.LANCZOS)
                        pil.save(path, quality=85)
                    else:
                        pil = Image.new("RGB", (200, 200), (150, 150, 150))
                        pil.save(path)
            except Exception:
                try:
                    if cv2 is not None:
                        cv2.imwrite(path, face_bgr)
                except Exception:
                    pass
            return path
        except Exception:
            return ""

    def _record_event_row(self, event, sid, name, entry_time, exit_time, thumb_path, class_name):
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        entry_ts = entry_time.strftime("%Y-%m-%d %H:%M:%S") if entry_time else None
        exit_ts = exit_time.strftime("%Y-%m-%d %H:%M:%S") if exit_time else None
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

        if thumb_path:
            try:
                pil = Image.open(thumb_path).convert("RGB")
                min_side = min(pil.width, pil.height)
                left = (pil.width - min_side) // 2
                top = (pil.height - min_side) // 2
                pil = pil.crop((left, top, left + min_side, top + min_side)).resize((80, 80), Image.LANCZOS)
            except Exception:
                pil = Image.new("RGB", (80, 80), (200, 200, 200))
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

        if self.auto_update_percent.get():
            try:
                self.calculate_and_update_percent()
            except Exception as e:
                print("Auto percent update failed:", e)

    def _append_row_to_autosave_files(self, row, class_name):
        class_name_safe = class_name or "global"
        base_dir = os.path.join("autosave", class_name_safe)
        os.makedirs(base_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(base_dir, f"{today_str}_attendance.csv")
        global_path = os.path.join(base_dir, "attendance_log.csv")
        write_daily_header = not os.path.exists(daily_path)
        write_global_header = not os.path.exists(global_path)
        with open(daily_path, "a", newline="", encoding="utf-8") as fd:
            w = csv.writer(fd)
            if write_daily_header:
                w.writerow(["timestamp", "event", "student_id", "name", "entry_time", "exit_time", "thumb_path", "class_name"])
            w.writerow(row)
        with open(global_path, "a", newline="", encoding="utf-8") as fg:
            wg = csv.writer(fg)
            if write_global_header:
                wg.writerow(["timestamp", "event", "student_id", "name", "entry_time", "exit_time", "thumb_path", "class_name"])
            wg.writerow(row)
        root_global_dir = os.path.join("autosave", "global")
        os.makedirs(root_global_dir, exist_ok=True)
        root_global_path = os.path.join(root_global_dir, "attendance_log.csv")
        write_root_header = not os.path.exists(root_global_path)
        with open(root_global_path, "a", newline="", encoding="utf-8") as fr:
            wr = csv.writer(fr)
            if write_root_header:
                wr.writerow(["timestamp", "event", "student_id", "name", "entry_time", "exit_time", "thumb_path", "class_name"])
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
                self.autosave_interval.set(str(interval))
            self._autosave_after_id = self.root.after(interval * 1000, self._autosave_timer_callback)
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
            conn = get_db_connection_and_ensure(parent=self.root)
            if conn is None:
                raise RuntimeError("DB connection failed for autosave")
            cursor = conn.cursor()
            for class_name, rows in grouped.items():
                for r in rows:
                    try:
                        cursor.execute("""
                            INSERT INTO attendance (timestamp, event, student_id, name, entry_time, exit_time, thumb_path, class_name)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, r)
                    except mysql.connector.Error as e:
                        print(f"Autosave DB insert failed: {e}")
            conn.commit()
            cursor.close()
            conn.close()

            for class_name, rows in grouped.items():
                base_dir = os.path.join("autosave", class_name)
                os.makedirs(base_dir, exist_ok=True)
                today_str = datetime.now().strftime("%Y-%m-%d")
                daily_path = os.path.join(base_dir, f"{today_str}_attendance.csv")
                global_path = os.path.join(base_dir, "attendance_log.csv")
                write_daily_header = not os.path.exists(daily_path)
                write_global_header = not os.path.exists(global_path)
                with open(daily_path, "a", newline="", encoding="utf-8") as fd:
                    w = csv.writer(fd)
                    if write_daily_header:
                        w.writerow(["timestamp", "event", "student_id", "name", "entry_time", "exit_time", "thumb_path", "class_name"])
                    for r in rows:
                        w.writerow(r)
                with open(global_path, "a", newline="", encoding="utf-8") as fg:
                    wg = csv.writer(fg)
                    if write_global_header:
                        wg.writerow(["timestamp", "event", "student_id", "name", "entry_time", "exit_time", "thumb_path", "class_name"])
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

    #  Manual
    def manual_entry_popup(self):
        win = Toplevel(self.root)
        win.transient(self.root)
        win.grab_set()
        win.title("Add Manual Attendance")
        win.geometry("460x240")
        Label(win, text="Student ID:", font=("Arial", 11)).pack(pady=(10, 2))
        e_id = Entry(win, width=40)
        e_id.pack()
        Label(win, text="Name:", font=("Arial", 11)).pack(pady=(8, 2))
        e_name = Entry(win, width=40)
        e_name.pack()
        Label(win, text="Timestamp (YYYY-MM-DD HH:MM:SS) optional:", font=("Arial", 9)).pack(pady=(8, 2))
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
            ok, sid_or_err = insert_session_entry_db(sid, name, when, None, self.class_entry.get().strip(), parent=self.root)
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
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], parent=win)
            if not path:
                return
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["timestamp", "event", "student_id", "name", "extra"])
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
        today = date.today().isoformat()
        conn = get_db_connection(parent=self.root, database=DB_NAME)
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
                            if ts.date().isoformat() == today:
                                continue
                        except Exception:
                            pass
                    remaining.append(ln)
                self.attendance_text.config(state=NORMAL)
                self.attendance_text.delete("1.0", END)
                for ln in remaining:
                    self.attendance_text.insert(END, ln + "\n")
                self.attendance_text.config(state=DISABLED)
                messagebox.showinfo("Cleared", f"Deleted {deleted} records for {today}", parent=self.root)
                self.status_label.config(text=f"Status: Cleared today's attendance ({deleted} rows)")
            except mysql.connector.Error as e:
                messagebox.showerror("Error", f"Failed to clear today's attendance:\n{e}", parent=self.root)
        else:
            messagebox.showerror("DB Error", "Cannot connect to DB to perform deletion.", parent=self.root)

    def remove_duplicate_db(self):
        if not messagebox.askyesno("Remove Duplicates", "This will remove duplicate attendance_sessions DB rows that have identical student_id and entry_time (keeps earliest id). Continue?", parent=self.root):
            return
        conn = get_db_connection(parent=self.root, database=DB_NAME)
        if not conn:
            messagebox.showerror("DB Error", "Cannot connect to DB.", parent=self.root)
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM attendance_sessions
                WHERE id NOT IN (
                    SELECT min_id FROM (
                        SELECT MIN(id) as min_id FROM attendance_sessions GROUP BY student_id, entry_time
                    ) as temp
                )
            """)
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
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
        except mysql.connector.Error as e:
            messagebox.showerror("Error", f"Failed to remove duplicates:\n{e}", parent=self.root)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        content = self.attendance_text.get("1.0", END).strip()
        if not content:
            messagebox.showinfo("Export", "Attendance log is empty.", parent=self.root)
            return
        lines = [ln for ln in content.splitlines() if ln.strip()]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["display_timestamp", "event_or_tag", "student_id", "name", "extra"])
                for ln in lines:
                    writer.writerow([ln])
            messagebox.showinfo("Export", f"Attendance exported to:\n{path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not write CSV:\n{e}", parent=self.root)

    # Backup UI  
    def backup_student_table(self, backup_base_path):
        use_mysqldump = getattr(self, "use_mysqldump_var", None) and bool(self.use_mysqldump_var.get())
        use_show_create = getattr(self, "use_showcreate_var", None) and bool(self.use_showcreate_var.get())
        return backup_student_table_to_paths(backup_base_path, parent=self.root, use_mysqldump=use_mysqldump, use_show_create=use_show_create)

    def ui_backup_student_table(self):
        base_path = filedialog.asksaveasfilename(defaultextension="", title="Choose backup filename base (no extension)", parent=self.root)
        if not base_path:
            return
        self.status_label.config(text="Status: Creating student table backup...")
        ok, info = self.backup_student_table(base_path)
        if not ok:
            sqlp, csvp, err = info
            messagebox.showerror("Backup failed", f"Student table backup failed: {err}", parent=self.root)
            self.status_label.config(text="Status: Backup failed")
        else:
            sqlp, csvp, _ = info
            messagebox.showinfo("Backup created", f"Backup created:\nSQL: {sqlp}\nCSV: {csvp}", parent=self.root)
            self.status_label.config(text=f"Status: Backup created ({os.path.basename(sqlp)})")

    def restore_student_table(self, sql_path):
        if not os.path.exists(sql_path):
            return False, "SQL file not found"
        if not messagebox.askyesno("Confirm restore", "Restoring will DROP and recreate the student table from the SQL file. Have you backed up current data? Continue?", parent=self.root):
            return False, "User canceled"
        try:
            sql_text = open(sql_path, "r", encoding="utf-8").read()
            conn = get_db_connection(parent=self.root, database=DB_NAME)
            if conn is None:
                return False, "DB connection failed for restore"
            cur = conn.cursor()
            for result in cur.execute(sql_text, multi=True):
                pass
            conn.commit()
            cur.close()
            conn.close()
            return True, None
        except mysql.connector.Error as e:
            return False, f"MySQL Error during restore: {e}"
        except Exception as e:
            return False, str(e)

    def ui_restore_student_table(self):
        sql_path = filedialog.askopenfilename(title="Select SQL backup file to restore", filetypes=[("SQL files", "*.sql"), ("All files", "*.*")], parent=self.root)
        if not sql_path:
            return
        ok, err = self.restore_student_table(sql_path)
        if not ok:
            messagebox.showerror("Restore failed", f"Restore failed: {err}", parent=self.root)
            self.status_label.config(text="Status: Restore failed")
        else:
            messagebox.showinfo("Restore complete", "Student table restored from backup. You may need to recompute attendance summary.", parent=self.root)
            self.status_label.config(text="Status: Student table restored")

    def ui_test_restore_student_table(self):
        sql_path = filedialog.askopenfilename(title="Select SQL backup file to test-restore", filetypes=[("SQL files", "*.sql"), ("All files", "*.*")], parent=self.root)
        if not sql_path:
            return
        if not messagebox.askyesno("Test Restore (Safe)", "This will restore the SQL backup into a temporary schema to verify it. This does NOT modify your live database. Continue?", parent=self.root):
            return
        self.status_label.config(text="Status: Running test-restore (temporary schema)...")
        ok, msg, details = test_restore_student_table(sql_path, parent=self.root)
        if ok:
            info = f"Test-restore succeeded.\nTemp schema: {details.get('temp_db')}\nStudent table rows: {details.get('student_row_count')}"
            messagebox.showinfo("Test Restore OK", info, parent=self.root)
            self.status_label.config(text="Status: Test-restore succeeded")
        else:
            messagebox.showerror("Test Restore Failed", f"{msg}\nDetails: {details}", parent=self.root)
            self.status_label.config(text="Status: Test-restore failed")

    def ui_compare_with_backup(self):
        sql_path = filedialog.askopenfilename(title="Select SQL backup file to compare", filetypes=[("SQL files", "*.sql"), ("All files", "*.*")], parent=self.root)
        if not sql_path:
            return
        if not messagebox.askyesno("Compare Backup", "This will restore the SQL backup into a temporary schema and compare the 'student' table schema and sample rows with the live database. Continue?", parent=self.root):
            return
        self.status_label.config(text="Status: Running comparison (temporary schema)...")
        ok, msg, details = compare_live_student_with_sql_backup(sql_path, parent=self.root, sample_rows=20)
        if not ok:
            messagebox.showerror("Compare Failed", f"{msg}\nDetails: {details}", parent=self.root)
            self.status_label.config(text="Status: Compare failed")
            return

        live_cols = details.get('live_columns', [])
        backup_cols = details.get('backup_columns', [])
        added_cols = [c for c in backup_cols if c not in live_cols]
        removed_cols = [c for c in live_cols if c not in backup_cols]
        live_count = details.get('live_row_count', 0)
        backup_count = details.get('backup_row_count', 0)
        sample_diffs = details.get('sample_diffs', [])

        summary = []
        summary.append(f"Live student columns: {live_cols}")
        summary.append(f"Backup student columns: {backup_cols}")
        if added_cols:
            summary.append(f"Columns in backup but missing live: {added_cols}")
        if removed_cols:
            summary.append(f"Columns in live but missing in backup: {removed_cols}")
        summary.append(f"Live row count: {live_count}")
        summary.append(f"Backup row count: {backup_count}")
        summary.append(f"Sample differing rows (up to {len(sample_diffs)}):")
        for d in sample_diffs[:10]:
            summary.append(f" - id={d['id']}, live={d['live_row']}, backup={d['backup_row']}")

        win = Toplevel(self.root)
        win.title("Comparison Result")
        txt = Text(win, width=120, height=30)
        txt.pack(fill=BOTH, expand=1)
        txt.insert(END, "\n".join(summary))
        txt.config(state=DISABLED)
        messagebox.showinfo("Compare Complete", "Comparison finished. See detail window.", parent=self.root)
        self.status_label.config(text="Status: Compare complete")

    # Scheduler 
    def choose_backup_folder(self):
        folder = filedialog.askdirectory(title="Choose backup folder", parent=self.root)
        if not folder:
            return
        self.schedule_folder_var.set(folder)
        self.scheduler.folder = folder
        self.scheduler.save_config()

    def toggle_scheduler(self):
        enabled = bool(self.schedule_enabled_var.get())
        self.scheduler.enabled = enabled
        self.scheduler.time_hhmm = self.schedule_time_var.get()
        self.scheduler.folder = self.schedule_folder_var.get()
        self.scheduler.save_config()
        if enabled:
            self.scheduler.start()
            self.status_label.config(text="Status: Nightly backup enabled")
        else:
            self.scheduler.stop()
            self.status_label.config(text="Status: Nightly backup disabled")

    def manual_backup_now(self):
        folder = self.schedule_folder_var.get() or "backups"
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(folder, f"{timestamp}")
        self.status_label.config(text="Status: Running manual backup...")
        ok, info = self.backup_student_table(base)
        if ok:
            sqlp, csvp, _ = info
            messagebox.showinfo("Backup complete", f"Backup created:\nSQL: {sqlp}\nCSV: {csvp}", parent=self.root)
            self.status_label.config(text=f"Status: Backup created ({os.path.basename(sqlp)})")
        else:
            messagebox.showerror("Backup failed", f"Backup failed: {info}", parent=self.root)
            self.status_label.config(text="Status: Manual backup failed")

    # Attendance Summary  
    def compute_attendance_summary(self):
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
            if not messagebox.askyesno("Confirm update", "You asked to update the student table. The app strongly recommends creating a backup first. Continue?", parent=self.root):
                return
            base_path = filedialog.asksaveasfilename(defaultextension="", filetypes=[("SQL + CSV backup base","*")], title="Choose backup filename base (no extension)", parent=self.root)
            if not base_path:
                if messagebox.askyesno("No backup selected", "No backup selected. Do you want to continue without updating the student table (skip update)?", parent=self.root):
                    update_student = False
                else:
                    return
            else:
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
        filters = []
        params = []
        if start_date:
            filters.append("DATE(entry_time) >= %s")
            params.append(start_date)
        if end_date:
            filters.append("DATE(entry_time) <= %s")
            params.append(end_date)
        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        conn = get_db_connection(parent=self.root, database=DB_NAME)
        if conn is None:
            raise RuntimeError("DB connection failed")

        cursor = conn.cursor(dictionary=True)
        q_total = f"SELECT COUNT(DISTINCT DATE(entry_time)) as c FROM attendance_sessions {where_clause}"
        cursor.execute(q_total, tuple(params))
        row = cursor.fetchone()
        total_class_days = int(row['c'] or 0)

        if filters:
            q_per = "SELECT student_id, COUNT(DISTINCT DATE(entry_time)) as d FROM attendance_sessions WHERE present = 1 AND " + " AND ".join(filters) + " GROUP BY student_id"
            per_params = list(params)
        else:
            q_per = "SELECT student_id, COUNT(DISTINCT DATE(entry_time)) as d FROM attendance_sessions WHERE present = 1 GROUP BY student_id"
            per_params = []

        cursor.execute(q_per, tuple(per_params))
        rows = cursor.fetchall()
        per_map = {str(r['student_id']): int(r['d']) for r in rows}

        cursor.execute("SELECT id, name FROM student")
        students = cursor.fetchall()

        with open(export_csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["student_id", "name", "days_present", "total_class_days", "attendance_percent"])
            for r in students:
                sid = r['id']
                name = r['name']
                sid_s = str(sid)
                dp = per_map.get(sid_s, 0)
                pct = round((100.0 * dp / total_class_days), 2) if total_class_days else 0.0
                w.writerow([sid_s, name, dp, total_class_days, pct])

        if update_student:
            conn2 = get_db_connection(parent=self.root, database=DB_NAME)
            cursor2 = conn2.cursor()
            update_q = "UPDATE student SET total_days_present = %s, attendance_percent = %s WHERE id = %s"
            for r in students:
                sid = r['id']
                sid_s = str(sid)
                dp = per_map.get(sid_s, 0)
                pct = round((100.0 * dp / total_class_days), 2) if total_class_days else 0.0
                try:
                    cursor2.execute(update_q, (dp, pct, sid))
                except mysql.connector.Error as e:
                    print("Failed to update student", sid, e)
            conn2.commit()
            cursor2.close()
            conn2.close()

    def calculate_and_update_percent(self):
        conn = get_db_connection(parent=self.root, database=DB_NAME)
        if conn is None:
            return
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(DISTINCT DATE(entry_time)) as c FROM attendance_sessions")
        total_days = int(cur.fetchone()['c'] or 0)
        cur.execute("SELECT student_id, COUNT(DISTINCT DATE(entry_time)) as d FROM attendance_sessions WHERE present = 1 GROUP BY student_id")
        rows = cur.fetchall()
        per_map = {str(r['student_id']): int(r['d']) for r in rows}
        cur.execute("SELECT id FROM student")
        students = cur.fetchall()
        update_q = "UPDATE student SET total_days_present = %s, attendance_percent = %s WHERE id = %s"
        for s in students:
            sid = s["id"]
            sid_s = str(sid)
            dp = per_map.get(sid_s, 0)
            pct = round((100.0 * dp / total_days), 2) if total_days else 0.0
            try:
                cur2 = conn.cursor()
                cur2.execute(update_q, (dp, pct, sid))
                cur2.close()
            except Exception:
                pass
        conn.commit()
        cur.close()
        conn.close()
        self.status_label.config(text=f"Status: Updated percents (total_days={total_days})")

    def show_attendance_graph(self):
        try:
            self.calculate_and_update_percent()
        except Exception:
            pass

        conn = get_db_connection(parent=self.root, database=DB_NAME)
        if conn is None:
            messagebox.showinfo("No data", "No students found to plot.", parent=self.root)
            return
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT name, attendance_percent FROM student ORDER BY attendance_percent DESC, name")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            messagebox.showinfo("No data", "No students found to plot.", parent=self.root)
            return

        names = [r["name"] for r in rows]
        percents = [float(r["attendance_percent"] or 0.0) for r in rows]

        fig = Figure(figsize=(8, max(3, len(names)*0.4)))
        ax = fig.add_subplot(111)
        ax.bar(range(len(names)), percents)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.set_ylabel("Attendance %")
        ax.set_ylim(0, 100)
        ax.set_title("Attendance Percentage per Student")

        win = Toplevel(self.root)
        win.title("Attendance Graph")
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill=BOTH, expand=1)

    #  Exit 
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
        Label(win, text="Are you sure you want to exit?", font=("Arial", 12, "bold")).pack(pady=(12, 6))
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
            win.after(1000, lambda: countdown(n - 1))

        countdown(timeout_seconds)

    def exit_fullscreen(self):
        try:
            try:
                self.perform_autosave(final=True)
            except Exception:
                pass
            try:
                self.scheduler.save_config()
                self.scheduler.stop()
            except Exception:
                pass
            try:
                self.root.attributes("-fullscreen", False)
            except Exception:
                pass
            if hasattr(self, "on_close"):
                try:
                    self.on_close()
                except Exception:
                    pass
            try:
                self.root.quit()
            except Exception:
                pass
        except Exception:
            try:
                self.root.quit()
            except Exception:
                pass

    #  entry 
    def simulate_entry(self):
        conn = get_db_connection_and_ensure()
        if conn is None:
            return
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, name FROM student LIMIT 1")
        r = cur.fetchone()
        if r:
            sid = r["id"]
            name = r["name"]
        else:
            demo_name = f"Demo Student {uuid.uuid4().hex[:6]}"
            cur2 = conn.cursor()
            cur2.execute("INSERT INTO student (name, misc) VALUES (%s, %s)", (demo_name, "demo"))
            sid = cur2.lastrowid
            name = demo_name
            conn.commit()
            cur2.close()
        cur.close()
        conn.close()

        pil = Image.new("RGB", (300, 300), (120, 200, 255))
        draw = ImageDraw.Draw(pil)
        try:
            fnt = ImageFont.load_default()
            draw.text((10, 140), f"{name}", font=fnt, fill=(0, 0, 0))
        except Exception:
            draw.text((10, 140), f"{name}", fill=(0, 0, 0))

        thumb_path = self._save_thumbnail_for_sid(pil, sid)
        entry_time = datetime.now()
        self._record_event_row("entry", sid, name, entry_time, None, thumb_path, self.class_entry.get().strip())
        insert_session_entry_db(sid, name, entry_time, None, self.class_entry.get().strip(), parent=self.root)
        self.status_label.config(text=f"Status: Simulated entry for {name}")

#  DB Insert 
def insert_event_db(row, parent=None):
    try:
        conn = get_db_connection_and_ensure(parent=parent)
        if conn is None:
            return False, "DB connection failed"
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (timestamp, event, student_id, name, entry_time, exit_time, thumb_path, class_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, row)
        conn.commit()
        cursor.close()
        conn.close()
        return True, None
    except mysql.connector.Error as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def insert_session_entry_db(sid, name, when, exit_time, class_name, parent=None):
    try:
        conn = get_db_connection_and_ensure(parent=parent)
        if conn is None:
            return False, "DB connection failed"
        cursor = conn.cursor()
        entry_time_str = when.strftime("%Y-%m-%d %H:%M:%S") if isinstance(when, datetime) else str(when)
        exit_time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, datetime) else exit_time
        cursor.execute("""
            INSERT INTO attendance_sessions (student_id, name, entry_time, exit_time, class_name, present)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(sid), str(name), entry_time_str, exit_time_str, class_name or "global", 1))
        rowid = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return True, rowid
    except mysql.connector.Error as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
 
if __name__ == "__main__":
    root = Tk()
    app = Attendance(root)
    root.protocol("WM_DELETE_WINDOW", app.confirm_exit)
    root.mainloop()
