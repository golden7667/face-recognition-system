from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk
from tkinter import messagebox
import mysql.connector
from mysql.connector import pooling
import os
import re
from dotenv import load_dotenv
import cv2
import numpy as np
import io

load_dotenv()

# Validation helpers 
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")   
def is_valid_email(email: str) -> bool:
    return bool(email and _EMAIL_RE.match(email))

def is_valid_phone(phone: str) -> bool:
    return bool(phone == "" or _PHONE_RE.match(phone))   


#  Connection pool helpers  
_mysql_pool = None

def init_mysql_pool():
    """Initialize the global MySQL connection pool. Call after DB has been created."""
    global _mysql_pool
    if _mysql_pool is not None:
        return

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASS = os.environ.get("DB_PASS", "golden123")
    DB_NAME = os.environ.get("DB_NAME", "facedb")

    try:
        _mysql_pool = pooling.MySQLConnectionPool(
            pool_name="student_pool",
            pool_size=5,
            pool_reset_session=True,
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4"
        )
    except Exception as exc:
        _mysql_pool = None
        messagebox.showerror("DB Pool Error", f"Could not create DB connection pool: {exc}", parent=None)


def get_pooled_connection(parent=None):
    """Return a connection from the pool or None if not available."""
    global _mysql_pool
    if _mysql_pool is None:
        init_mysql_pool()
    if _mysql_pool is None:
        if parent:
            messagebox.showerror("DB Error", "Database connection pool is not available.", parent=parent)
        return None
    try:
        return _mysql_pool.get_connection()
    except Exception as e:
        if parent:
            messagebox.showerror("DB Error", f"Could not get connection from pool: {e}", parent=parent)
        return None


#  Main Application 
class Students:
    def __init__(self, root):
        self.root = root
        self.root.geometry("2000x790+0+0")
        self.root.state('zoomed')  
        self.root.title("Student Management System")

        
        try:
            img1 = Image.open("image/st1.jfif").resize((500, 130), Image.LANCZOS)
            self.photoimg1 = ImageTk.PhotoImage(img1)
            f_lbl1 = Label(self.root, image=self.photoimg1)
            f_lbl1.place(x=0, y=0, width=500, height=150)
        except Exception:
            pass

        try:
            img2 = Image.open("image/st2.jfif").resize((500, 130), Image.LANCZOS)
            self.photoimg2 = ImageTk.PhotoImage(img2)
            f_lbl2 = Label(self.root, image=self.photoimg2)
            f_lbl2.place(x=500, y=0, width=500, height=150)
        except Exception:
            pass

        try:
            img3 = Image.open("image/st4.jfif").resize((500, 130), Image.LANCZOS)
            self.photoimg3 = ImageTk.PhotoImage(img3)
            f_lbl3 = Label(self.root, image=self.photoimg3)
            f_lbl3.place(x=1000, y=0, width=500, height=150)
        except Exception:
            pass

        try:
            img4 = Image.open("image/studen.webp").resize((500, 130), Image.LANCZOS)
            self.photoimg4 = ImageTk.PhotoImage(img4)
            f_lbl4 = Label(self.root, image=self.photoimg4)
            f_lbl4.place(x=1500, y=0, width=500, height=150)
        except Exception:
            pass

        # bg image
        try:
            img = Image.open("image/Ethical-Hacking.jpg").resize((2160, 910), Image.LANCZOS)
            self.photoimg = ImageTk.PhotoImage(img)
            f_lbl = Label(self.root, image=self.photoimg)
            f_lbl.place(x=0, y=130, width=2160, height=910)
        except Exception:
            pass

        title_lbl = Label(self.root,
                          text="Student Management System",
                          font=("Arial", 30, "bold"),
                          fg="black",
                          bg="white")
        title_lbl.place(x=0, y=130, width=2000, height=50)

        # frame
        main_frame = Frame(self.root, bd=3, relief=RIDGE, bg="lightgray")
        main_frame.place(x=0, y=180, width=2140, height=800)
        Label(main_frame, font=("Arial", 20, "bold"), fg="black", bg="lightgray").pack(pady=20)

        # left
        Left_Frame = LabelFrame(main_frame, text="Student Information", bd=4, relief=RIDGE,
                                bg="lightgray", font=("Arial", 12, "bold"))
        Left_Frame.place(x=10, y=10, width=760, height=700)

        try:
            img_left = Image.open("image/st5.jpg").resize((760, 100), Image.LANCZOS)
            self.photoimg_left = ImageTk.PhotoImage(img_left)
            img_label = Label(Left_Frame, image=self.photoimg_left, bg="lightgray")
            img_label.pack(pady=0.5)
        except Exception:
            pass

        # Current Course
        Current_Course_Frame = LabelFrame(Left_Frame, text="Current Course", bd=4, relief=RIDGE,
                                         bg="white", font=("Arial", 12, "bold"))
        Current_Course_Frame.place(x=10, y=120, width=840, height=150)

        # Vars
        self.ver_dep = StringVar(value="Select Department")
        self.ver_course = StringVar(value="Select Course")
        self.ver_year = StringVar(value="Select Year")
        self.ver_sem = StringVar(value="Select Semester")

        Label(Current_Course_Frame, text="Department", bg="black", fg="white",
              font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
        dep_combo = ttk.Combobox(Current_Course_Frame, textvariable=self.ver_dep,
                                 font=("Arial", 11, "bold"), width=18, state="readonly")
        dep_combo["values"] = ("Select Department", "Computer Science", "IT", "Civil", "Mechanical")
        dep_combo.current(0)
        dep_combo.grid(row=0, column=1, padx=10, pady=10, sticky=W)

        Label(Current_Course_Frame, text="Course", bg="black", fg="white",
              font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, pady=10, sticky=W)
        course_combo = ttk.Combobox(Current_Course_Frame, textvariable=self.ver_course,
                                    font=("Arial", 11, "bold"), width=18, state="readonly")
        course_combo["values"] = ("Select Course", "BE", "Python", "English", "Maths")
        course_combo.current(0)
        course_combo.grid(row=0, column=3, padx=10, pady=10, sticky=W)

        Label(Current_Course_Frame, text="Year", bg="black", fg="white",
              font=("Arial", 11, "bold")).grid(row=1, column=0, padx=10, pady=10, sticky=W)
        year_combo = ttk.Combobox(Current_Course_Frame, textvariable=self.ver_year,
                                  font=("Arial", 11, "bold"), width=18, state="readonly")
        year_combo["values"] = ("Select Year", "2022", "2023", "2024", "2025", "2026")
        year_combo.current(0)
        year_combo.grid(row=1, column=1, padx=10, pady=10, sticky=W)

        Label(Current_Course_Frame, text="Semester", bg="black", fg="white",
              font=("Arial", 11, "bold")).grid(row=1, column=2, padx=10, pady=10, sticky=W)
        sem_combo = ttk.Combobox(Current_Course_Frame, textvariable=self.ver_sem,
                                 font=("Arial", 11, "bold"), width=18, state="readonly")
        sem_combo["values"] = ("Select Semester", "1", "2", "3", "4", "5", "6", "7", "8")
        sem_combo.current(0)
        sem_combo.grid(row=1, column=3, padx=10, pady=10, sticky=W)

        # student information in class
        Class_student_Frame = LabelFrame(Left_Frame, text="Student Information", bd=4, relief=RIDGE,
                                         bg="white", font=("Arial", 10, "bold"))
        Class_student_Frame.place(x=10, y=250, width=740, height=400)

        # Form vars
        self.ver_studentid = StringVar()
        self.ver_studentname = StringVar()
        self.ver_classdivision = StringVar()
        self.ver_roll = StringVar()
        self.ver_gender = StringVar()
        self.ver_dob = StringVar()
        self.ver_emailid = StringVar()
        self.ver_phoneno = StringVar()
        self.ver_add = StringVar()
        self.ver_bolodgroup = StringVar()  
        self.ver_radiobtn = StringVar(value="no")

        # Form layout (kept from original)
        Studenid_label = Label(Class_student_Frame, text="StudentID", bg="black", fg="white",
                               font=("Arial", 10, "bold"))
        Studenid_label.grid(row=0, column=0, padx=10, pady=10, sticky=W)
        self.StudentId_entry = Entry(Class_student_Frame, textvariable=self.ver_studentid, font=("Arial", 10))
        self.StudentId_entry.grid(row=0, column=1, padx=10, pady=10, sticky=W)

        studentname_label = Label(Class_student_Frame, text="Student Name", bg="black", fg="white",
                                  font=("Arial", 10, "bold"))
        studentname_label.grid(row=0, column=3, padx=10, pady=10, sticky=W)
        self.studenname_entry = Entry(Class_student_Frame, textvariable=self.ver_studentname, font=("Arial", 10))
        self.studenname_entry.grid(row=0, column=4, padx=10, pady=10, sticky=W)

        classdivision_label = Label(Class_student_Frame, text="Class Section", bg="black", fg="white",
                                    font=("Arial", 10, "bold"))
        classdivision_label.grid(row=1, column=0, padx=10, pady=10, sticky=W)
        self.classdivision_entry = Entry(Class_student_Frame, textvariable=self.ver_classdivision, font=("Arial", 10))
        self.classdivision_entry.grid(row=1, column=1, padx=10, pady=10, sticky=W)

        roll_label = Label(Class_student_Frame, text="Rollno", bg="black", fg="white", font=("Arial", 10, "bold"))
        roll_label.grid(row=1, column=3, padx=10, pady=10, sticky=W)
        self.roll_entry = Entry(Class_student_Frame, textvariable=self.ver_roll, font=("Arial", 10))
        self.roll_entry.grid(row=1, column=4, padx=10, pady=10, sticky=W)

        gender_label = Label(Class_student_Frame, text="Gender", bg="black", fg="white", font=("Arial", 10, "bold"))
        gender_label.grid(row=2, column=0, padx=10, pady=10, sticky=W)
        self.gender_entry = Entry(Class_student_Frame, textvariable=self.ver_gender, font=("Arial", 10))
        self.gender_entry.grid(row=2, column=1, padx=10, pady=10, sticky=W)

        dob_label = Label(Class_student_Frame, text="D.O.B", bg="black", fg="white", font=("Arial", 10, "bold"))
        dob_label.grid(row=2, column=3, padx=10, pady=10, sticky=W)
        self.dob_entry = Entry(Class_student_Frame, textvariable=self.ver_dob, font=("Arial", 10))
        self.dob_entry.grid(row=2, column=4, padx=10, pady=10, sticky=W)

        emailid_label = Label(Class_student_Frame, text="Email Id", bg="black", fg="white", font=("Arial", 10, "bold"))
        emailid_label.grid(row=3, column=0, padx=10, pady=10, sticky=W)
        self.emailid_entry = Entry(Class_student_Frame, textvariable=self.ver_emailid, font=("Arial", 10))
        self.emailid_entry.grid(row=3, column=1, padx=10, pady=10, sticky=W)

        phoneno_label = Label(Class_student_Frame, text="Phone No", bg="black", fg="white", font=("Arial", 10, "bold"))
        phoneno_label.grid(row=3, column=3, padx=10, pady=10, sticky=W)
        self.phoneno_entry = Entry(Class_student_Frame, textvariable=self.ver_phoneno, font=("Arial", 11))
        self.phoneno_entry.grid(row=3, column=4, padx=10, pady=10, sticky=W)

        addr_label = Label(Class_student_Frame, text="Address", bg="black", fg="white", font=("Arial", 10, "bold"))
        addr_label.grid(row=4, column=0, padx=10, pady=10, sticky=W)
        self.addr_entry = Entry(Class_student_Frame, textvariable=self.ver_add, font=("Arial", 10))
        self.addr_entry.grid(row=4, column=1, padx=10, pady=10, sticky=W)

        bloodgroup_label = Label(Class_student_Frame, text="Blood Group", bg="black", fg="white",
                                 font=("Arial", 10, "bold"))
        bloodgroup_label.grid(row=4, column=3, padx=10, pady=10, sticky=W)
        self.bloodgroup_entry = Entry(Class_student_Frame, textvariable=self.ver_bolodgroup, font=("Arial", 10))
        self.bloodgroup_entry.grid(row=4, column=4, padx=10, pady=10, sticky=W)

        # radio
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.TRadiobutton", background="white", foreground="black", font=("Arial", 10, "bold"))
        radiobtn1 = ttk.Radiobutton(Class_student_Frame, text="Yes Simple Pic", variable=self.ver_radiobtn, value="yes")
        radiobtn1.grid(row=5, column=0, padx=10, pady=10, sticky=W)
        radiobtn2 = ttk.Radiobutton(Class_student_Frame, text="No Simple Pic", variable=self.ver_radiobtn, value="no")
        radiobtn2.grid(row=5, column=1, padx=10, pady=10, sticky=W)

        # button frames
        btn_frame = Frame(Class_student_Frame, bd=2, relief=RIDGE, bg="white")
        btn_frame.place(x=0, y=260, width=645, height=38)

        save_btn = Button(btn_frame, text="Save", command=self.add_data, width=15,
                          font=("time new roman", 12, "bold"), bg="blue", fg="white")
        save_btn.grid(row=0, column=0)

        update_btn = Button(btn_frame, text="Update", command=self.update_data, width=15,
                            font=("time new roman", 12, "bold"), bg="blue", fg="white")
        update_btn.grid(row=0, column=1)

        delete_btn = Button(btn_frame, text="Delete", command=self.delete_data, width=15,
                            font=("time new roman", 12, "bold"), bg="blue", fg="white")
        delete_btn.grid(row=0, column=2)

        reset_btn = Button(btn_frame, text="Reset", command=self.reset_data, width=15,
                           font=("time new roman", 13, "bold"), bg="blue", fg="white")
        reset_btn.grid(row=0, column=3)

        btn_frame2 = Frame(Class_student_Frame, bd=2, relief=RIDGE, bg="white")
        btn_frame2.place(x=1, y=300, width=550, height=38)

        photo_btn = Button(btn_frame2, text="Take Simple photo", width=23,
                           font=("time new roman", 15, "bold"), bg="blue", fg="white")
        photo_btn.grid(row=0, column=0)

        uplphoto_btn = Button(btn_frame2, text="Upload simple Photo", width=23,
                              font=("time new roman", 15, "bold"), bg="blue", fg="white")
        uplphoto_btn.grid(row=0, column=1)

        # wire buttons to the OpenCV methods
        photo_btn.config(command=self.take_photo)
        uplphoto_btn.config(command=self.upload_photo)

        # right
        Right_Frame = LabelFrame(main_frame, text="Attendance Details", bd=4, relief=RIDGE,
                                 bg="lightgray", font=("Arial", 12, "bold"))
        Right_Frame.place(x=780, y=10, width=780, height=700)

        try:
            img_right = Image.open("image/studen.webp").resize((760, 100), Image.LANCZOS)
            self.photoimg_right = ImageTk.PhotoImage(img_right)
            img_label = Label(Right_Frame, image=self.photoimg_right, bg="lightgray")
            img_label.pack(pady=0.5)
        except Exception:
            pass

        # search
        search_Frame = LabelFrame(Right_Frame, text="Search System", bd=4, relief=RIDGE,
                                  bg="white", font=("Arial", 12, "bold"))
        search_Frame.place(x=10, y=120, width=750, height=120)

        search_label = Label(search_Frame, text="Search By", bg="black", fg="white",
                             font=("Arial", 10, "bold"))
        search_label.grid(row=0, column=0, padx=10, pady=10, sticky=W)

        self.select_combo = ttk.Combobox(search_Frame, font=("Arial", 11, "bold"), width=18, state="readonly")
        self.select_combo["values"] = ("Select Option", "Student ID", "Name", "Course", "Semester")
        self.select_combo.current(0)
        self.select_combo.grid(row=0, column=1, padx=10, pady=10, sticky=W)

        self.search_entry = Entry(search_Frame, font=("Arial", 10))
        self.search_entry.grid(row=0, column=2, padx=10, pady=10, sticky=W)

        search_btn = Button(search_Frame, text="Search", command=self.search_data,
                            font=("Arial", 10, "bold"), bg="blue", fg="white")
        search_btn.grid(row=0, column=3, padx=10, pady=10, sticky=W)

        clear_btn = Button(search_Frame, text="Clear", font=("Arial", 10, "bold"),
                           bg="red", fg="white", command=lambda: self.search_entry.delete(0, END))
        clear_btn.grid(row=0, column=4, padx=10, pady=10, sticky=W)

        # table
        table_Frame = Frame(Right_Frame, bd=4, relief=RIDGE, bg="white")
        table_Frame.place(x=10, y=250, width=750, height=400)

        scroll_x = ttk.Scrollbar(table_Frame, orient=HORIZONTAL)
        scroll_y = ttk.Scrollbar(table_Frame, orient=VERTICAL)

        self.student_table = ttk.Treeview(table_Frame,
                                          columns=("dep", "course", "year", "sem", "id", "name", "div", "roll",
                                                   "gender", "DOB", "Email", "address", "bloodgroup", "photo"),
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set,
                                          show="headings")
        scroll_x.config(command=self.student_table.xview)
        scroll_y.config(command=self.student_table.yview)

        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.student_table.pack(fill=BOTH, expand=1)

        # headings
        self.student_table.heading("dep", text="Department")
        self.student_table.heading("course", text="Course")
        self.student_table.heading("year", text="Year")
        self.student_table.heading("sem", text="Semester")
        self.student_table.heading("id", text="Student ID")
        self.student_table.heading("name", text="Name")
        self.student_table.heading("div", text="Division")
        self.student_table.heading("roll", text="Roll No")
        self.student_table.heading("gender", text="Gender")
        self.student_table.heading("DOB", text="D.O.B")
        self.student_table.heading("Email", text="Email")
        self.student_table.heading("address", text="Address")
        self.student_table.heading("bloodgroup", text="Blood Group")
        self.student_table.heading("photo", text="Photo")

        self.student_table.column("dep", width=120)
        self.student_table.column("course", width=80)
        self.student_table.column("year", width=60)
        self.student_table.column("sem", width=60)
        self.student_table.column("id", width=100)
        self.student_table.column("name", width=150)

        # bind selection
        self.student_table.bind("<ButtonRelease-1>", self.get_cursor)

        # Ensure DB and table exist,
        self.ensure_db_and_table()
        init_mysql_pool()
        self.fetch_data()

    #  DB creation & connection 
    def ensure_db_and_table(self):
        
        DB_HOST = os.environ.get("DB_HOST", "localhost")
        DB_USER = os.environ.get("DB_USER", "root")
        DB_PASS = os.environ.get("DB_PASS", "golden1234")
        DB_NAME = os.environ.get("DB_NAME", "facedb")
       

        # Connect without database to create it if needed
        try:
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showwarning("DB Warning", f"Could not create database automatically: {err}\nIf the database exists, the app will continue to try to connect.", parent=self.root)

        # Now ensure table exists
        try:
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
            cursor = conn.cursor()
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS `student` (
                `dep` VARCHAR(100),
                `course` VARCHAR(100),
                `year` VARCHAR(10),
                `sem` VARCHAR(10),
                `id` VARCHAR(50) PRIMARY KEY,
                `name` VARCHAR(255),
                `div` VARCHAR(50),
                `roll` VARCHAR(50),
                `gender` VARCHAR(20),
                `dob` VARCHAR(50),
                `email` VARCHAR(255),
                `address` TEXT,
                `bloodgroup` VARCHAR(50),
                `photo` VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("DB Error", f"Could not ensure student table exists: {err}", parent=self.root)

    # Add Data
    def add_data(self):
        dep = self.ver_dep.get()
        course = self.ver_course.get()
        year = self.ver_year.get()
        sem = self.ver_sem.get()
        studentid = self.ver_studentid.get().strip()
        studentname = self.ver_studentname.get().strip()
        classdivision = self.ver_classdivision.get().strip()
        roll = self.ver_roll.get().strip()
        gender = self.ver_gender.get().strip()
        dob = self.ver_dob.get().strip()
        emailid = self.ver_emailid.get().strip()
        phoneno = self.ver_phoneno.get().strip()
        add = self.ver_add.get().strip()
        bloodgroup = self.ver_bolodgroup.get().strip()
        photo = self.ver_radiobtn.get().strip()

        # Basic validation
        if dep == "Select Department" or course == "Select Course" or studentid == "" or studentname == "":
            messagebox.showerror("Error", "Please enter Department, Course, Student ID and Student Name", parent=self.root)
            return

        if emailid and not is_valid_email(emailid):
            messagebox.showerror("Invalid email", "Please enter a valid email address.", parent=self.root)
            return

        if phoneno and not is_valid_phone(phoneno):
            messagebox.showerror("Invalid phone", "Please enter a valid phone number (digits, +, spaces allowed).", parent=self.root)
            return

        conn = get_pooled_connection(parent=self.root)
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO `student`
                (`dep`, `course`, `year`, `sem`, `id`, `name`, `div`, `roll`, `gender`, `dob`, `email`, `address`, `bloodgroup`, `photo`)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (dep, course, year, sem, studentid, studentname, classdivision, roll, gender, dob, emailid, add, bloodgroup, photo))
            conn.commit()
            messagebox.showinfo("Success", "Student details added successfully!", parent=self.root)
            self.fetch_data()
            self.reset_data()
        except mysql.connector.IntegrityError:
            messagebox.showerror("Error", "Student ID already exists. Use Update or different ID.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Due to: {str(e)}", parent=self.root)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    #  Fetch Data 
    def fetch_data(self):
        conn = get_pooled_connection(parent=self.root)
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT `dep`, `course`, `year`, `sem`, `id`, `name`, `div`, `roll`, `gender`, `dob`, `email`, `address`, `bloodgroup`, `photo` FROM `student`")
            rows = cursor.fetchall()
            self.student_table.delete(*self.student_table.get_children())
            for row in rows:
                self.student_table.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Due to: {str(e)}", parent=self.root)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    #  Get selected row
    def get_cursor(self, event=""):
        selected = self.student_table.focus()
        if not selected:
            return
        data = self.student_table.item(selected, "values")
        if data:
            self.ver_dep.set(data[0])
            self.ver_course.set(data[1])
            self.ver_year.set(data[2])
            self.ver_sem.set(data[3])
            self.ver_studentid.set(data[4])
            self.ver_studentname.set(data[5])
            self.ver_classdivision.set(data[6])
            self.ver_roll.set(data[7])
            self.ver_gender.set(data[8])
            self.ver_dob.set(data[9])
            self.ver_emailid.set(data[10])
            self.ver_add.set(data[11])
            self.ver_bolodgroup.set(data[12])
            self.ver_radiobtn.set(data[13] if len(data) > 13 else "no")

    #  Update Data 
    def update_data(self):
        sid = self.ver_studentid.get().strip()
        if sid == "":
            messagebox.showerror("Error", "Please select a student to update", parent=self.root)
            return

        emailid = self.ver_emailid.get().strip()
        phoneno = self.ver_phoneno.get().strip()
        if emailid and not is_valid_email(emailid):
            messagebox.showerror("Invalid email", "Please enter a valid email address.", parent=self.root)
            return
        if phoneno and not is_valid_phone(phoneno):
            messagebox.showerror("Invalid phone", "Please enter a valid phone number (digits, +, spaces allowed).", parent=self.root)
            return

        conn = get_pooled_connection(parent=self.root)
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE `student` SET
                    `dep`=%s, `course`=%s, `year`=%s, `sem`=%s,
                    `name`=%s, `div`=%s, `roll`=%s, `gender`=%s,
                    `dob`=%s, `email`=%s, `address`=%s, `bloodgroup`=%s, `photo`=%s
                WHERE `id`=%s
            """, (
                self.ver_dep.get(), self.ver_course.get(), self.ver_year.get(), self.ver_sem.get(),
                self.ver_studentname.get(), self.ver_classdivision.get(), self.ver_roll.get(),
                self.ver_gender.get(), self.ver_dob.get(), self.ver_emailid.get(), self.ver_add.get(),
                self.ver_bolodgroup.get(), self.ver_radiobtn.get(), sid
            ))
            conn.commit()
            if cursor.rowcount == 0:
                messagebox.showwarning("Warning", "No student found with this ID.", parent=self.root)
            else:
                messagebox.showinfo("Success", "Student details updated successfully!", parent=self.root)
            self.fetch_data()
        except Exception as e:
            messagebox.showerror("Error", f"Due to: {str(e)}", parent=self.root)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # Delete Data 
    def delete_data(self):
        sid = self.ver_studentid.get().strip()
        if sid == "":
            messagebox.showerror("Error", "Please select a student to delete", parent=self.root)
            return

        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this student?", parent=self.root)
        if not confirm:
            return

        conn = get_pooled_connection(parent=self.root)
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM `student` WHERE `id`=%s", (sid,))
            conn.commit()
            if cursor.rowcount == 0:
                messagebox.showwarning("Warning", "No student found with this ID.", parent=self.root)
            else:
                messagebox.showinfo("Success", "Student details deleted successfully!", parent=self.root)
            self.fetch_data()
            self.reset_data()
        except Exception as e:
            messagebox.showerror("Error", f"Due to: {str(e)}", parent=self.root)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # Reset 
    def reset_data(self):
        self.ver_dep.set("Select Department")
        self.ver_course.set("Select Course")
        self.ver_year.set("Select Year")
        self.ver_sem.set("Select Semester")
        self.ver_studentid.set("")
        self.ver_studentname.set("")
        self.ver_classdivision.set("")
        self.ver_roll.set("")
        self.ver_gender.set("")
        self.ver_dob.set("")
        self.ver_emailid.set("")
        self.ver_phoneno.set("")
        self.ver_add.set("")
        self.ver_bolodgroup.set("")
        self.ver_radiobtn.set("no")

    # Search 
    def search_data(self):
        option = self.select_combo.get()
        text = self.search_entry.get().strip()
        if option == "Select Option" or text == "":
            messagebox.showerror("Error", "Please select a search criteria and enter text", parent=self.root)
            return

        field_map = {
            "Student ID": "id",
            "Name": "name",
            "Course": "course",
            "Semester": "sem"
        }
        field = field_map.get(option)
        if not field:
            messagebox.showerror("Error", "Invalid search option", parent=self.root)
            return

        conn = get_pooled_connection(parent=self.root)
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            query = f"SELECT `dep`, `course`, `year`, `sem`, `id`, `name`, `div`, `roll`, `gender`, `dob`, `email`, `address`, `bloodgroup`, `photo` FROM `student` WHERE `{field}` LIKE %s"
            cursor.execute(query, (f"%{text}%",))
            rows = cursor.fetchall()
            self.student_table.delete(*self.student_table.get_children())
            for row in rows:
                self.student_table.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Due to: {str(e)}", parent=self.root)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # OpenCV functions added
    def take_photo(self):
        sid = self.ver_studentid.get().strip()
        if sid == "":
            messagebox.showerror("Error", "Please enter Student ID before taking photo.", parent=self.root)
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Camera Error", "Cannot open webcam.", parent=self.root)
            return

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        while True:
            ret, img = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.imshow("Press S to Save Photo | Q to Quit", img)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                os.makedirs("data", exist_ok=True)
                filename = f"data/{sid}.jpg"

                try:
                    if len(faces) > 0:
                        (x, y, w, h) = faces[0]
                        face_img = img[y:y+h, x:x+w]
                        face_img = cv2.resize(face_img, (200, 200))
                        cv2.imwrite(filename, face_img)
                    else:
                        # fallback - save full frame resized
                        resized = cv2.resize(img, (300, 300))
                        cv2.imwrite(filename, resized)

                    # update DB to store filename
                    conn = get_pooled_connection(parent=self.root)
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE `student` SET `photo`=%s WHERE `id`=%s", (filename, sid))
                            conn.commit()
                            cursor.close()
                        except Exception as e:
                            messagebox.showwarning("DB Warning", f"Saved image but failed to update DB: {e}", parent=self.root)
                        finally:
                            try:
                                conn.close()
                            except Exception:
                                pass

                    self.ver_radiobtn.set("yes")
                    messagebox.showinfo("Saved", f"Photo saved as {filename}", parent=self.root)
                finally:
                    break

            elif key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        self.fetch_data()


    def upload_photo(self):
        sid = self.ver_studentid.get().strip()
        if sid == "":
            messagebox.showerror("Error", "Please enter Student ID before uploading photo.", parent=self.root)
            return

        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
        )

        if not file_path:
            return

        img = cv2.imread(file_path)
        if img is None:
            messagebox.showerror("Error", "Invalid image file.", parent=self.root)
            return

        os.makedirs("data", exist_ok=True)
        filename = f"data/{sid}_upl.jpg"

        try:
            resized = cv2.resize(img, (300, 300))
            cv2.imwrite(filename, resized)

            # update DB to store filename
            conn = get_pooled_connection(parent=self.root)
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE `student` SET `photo`=%s WHERE `id`=%s", (filename, sid))
                    conn.commit()
                    cursor.close()
                except Exception as e:
                    messagebox.showwarning("DB Warning", f"Uploaded image saved but failed to update DB: {e}", parent=self.root)
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            self.ver_radiobtn.set("yes")
            messagebox.showinfo("Saved", f"Image uploaded as {filename}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save uploaded image: {e}", parent=self.root)
        finally:
            self.fetch_data()

            sid = self.ver_studentid.get().strip()
            if sid == "":
                messagebox.showerror("Error", "Please enter Student ID before uploading photo.", parent=self.root)
                return

            file_path = filedialog.askopenfilename(
                title="Select Image",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
            )

            if not file_path:
                return

            img = cv2.imread(file_path)
            if img is None:
                messagebox.showerror("Error", "Invalid image file.", parent=self.root)
                return

        os.makedirs("data", exist_ok=True)
        filename = f"data/{sid}_upl.jpg"
        resized = cv2.resize(img, (300, 300))
        cv2.imwrite(filename, resized)

        self.ver_radiobtn.set("yes")
        messagebox.showinfo("Saved", f"Image uploaded as {filename}", parent=self.root)
        self.fetch_data()
    


if __name__ == "__main__":
    root = Tk()
    app = Students(root)
    root.mainloop()
