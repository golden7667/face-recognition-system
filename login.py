import tkinter as tk
from tkinter import messagebox
import json
import os
import bcrypt
from PIL import Image, ImageTk 

 
USERS_FILE = "users.json"



def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)



def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False



from main import FaceDetectionApp

 
root = None
register_window = None
forgot_window = None

user_entry = None
pass_entry = None

reg_user_entry = None
reg_pass_entry = None
reg_confirm_entry = None

forgot_user_entry = None

 
def open_fullscreen(win: tk.Tk | tk.Toplevel):
    """Make a Tk/Toplevel window full screen / maximized."""
    try:
        win.state("zoomed")  
    except Exception:
        win.attributes("-zoomed", True)  


def set_background_image(win: tk.Tk | tk.Toplevel, image_path: str = "background.jpg"):
    """
    Set a background image that fills the full window.
    Assumes window is already fullscreen or has final size.
    """
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()

    try:
        img = Image.open(r"image\resized_Chatobots-legal-key-issues.jpg")
        img = img.resize((screen_w, screen_h))
        photo = ImageTk.PhotoImage(img)

        bg_label = tk.Label(win, image=photo)
        bg_label.image = photo  # keep reference
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        return bg_label
    except Exception as e:
        print("Error loading background image:", e)
        win.configure(bg="black")
        return None

 
def open_face_app(username: str):
    app_root = tk.Tk()
    open_fullscreen(app_root)
    app_root.title(f"Face Detection - {username}")
    app = FaceDetectionApp(app_root)
    app_root.mainloop()


 
def login_function():
    username = user_entry.get().strip()
    password = pass_entry.get().strip()

    if username == "" or password == "":
        messagebox.showwarning("Error", "Please fill all fields")
        return

    users = load_users()
    user = users.get(username)

    if not user:
        messagebox.showerror("Error", "Invalid username or password")
        return

    if not check_password(password, user["password"]):
        messagebox.showerror("Error", "Invalid username or password")
        return

    messagebox.showinfo("Success", f"Welcome {username}")
    root.destroy()
    open_face_app(username)


def register_user():
    new_user = reg_user_entry.get().strip()
    new_pass = reg_pass_entry.get().strip()
    confirm_pass = reg_confirm_entry.get().strip()

    if new_user == "" or new_pass == "" or confirm_pass == "":
        messagebox.showwarning("Error", "Please fill all fields")
        return

    if new_pass != confirm_pass:
        messagebox.showerror("Error", "Passwords do not match")
        return

    users = load_users()

    if new_user in users:
        messagebox.showerror("Error", "Username already exists")
        return

    users[new_user] = {
        "username": new_user,
        "password": hash_password(new_pass),
    }

    save_users(users)
    messagebox.showinfo("Success", "Account created successfully")
    register_window.destroy()


def reset_password():
    username = forgot_user_entry.get().strip()
    users = load_users()

    if username == "":
        messagebox.showwarning("Error", "Enter username")
        return

    if username not in users:
        messagebox.showerror("Error", "User not found")
        return

    messagebox.showinfo(
        "Message",
        "Sorry, password cannot be recovered.\nPlease register a new account."
    )
    forgot_window.destroy()


 
def open_register_window():
    global register_window, reg_user_entry, reg_pass_entry, reg_confirm_entry

    register_window = tk.Toplevel(root)
    open_fullscreen(register_window)
    register_window.title("Register")

    set_background_image(register_window, "background.jpg")

    # Center frame
    frame = tk.Frame(register_window, bg="#000000", bd=2)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(frame, text="REGISTER", font=("Arial", 30, "bold"),
             bg="#000000", fg="white").pack(pady=20)

    tk.Label(frame, text="Username", font=("Arial", 18),
             bg="#000000", fg="white").pack()
    reg_user_entry = tk.Entry(frame, font=("Arial", 18))
    reg_user_entry.pack(pady=5)

    tk.Label(frame, text="Password", font=("Arial", 18),
             bg="#000000", fg="white").pack()
    reg_pass_entry = tk.Entry(frame, show="*", font=("Arial", 18))
    reg_pass_entry.pack(pady=5)

    tk.Label(frame, text="Confirm Password", font=("Arial", 18),
             bg="#000000", fg="white").pack()
    reg_confirm_entry = tk.Entry(frame, show="*", font=("Arial", 18))
    reg_confirm_entry.pack(pady=5)

    tk.Button(frame, text="Register", font=("Arial", 20),
              bg="green", fg="white", command=register_user
              ).pack(pady=20, fill="x")


 
def open_forgot_window():
    global forgot_window, forgot_user_entry

    forgot_window = tk.Toplevel(root)
    open_fullscreen(forgot_window)
    forgot_window.title("Forgot Password")

    set_background_image(forgot_window, "background.jpg")

    frame = tk.Frame(forgot_window, bg="#000000", bd=2)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(frame, text="FORGOT PASSWORD", font=("Arial", 30, "bold"),
             bg="#000000", fg="white").pack(pady=20)

    tk.Label(frame, text="Enter Username", font=("Arial", 20),
             bg="#000000", fg="white").pack()
    forgot_user_entry = tk.Entry(frame, font=("Arial", 18))
    forgot_user_entry.pack(pady=10)

    tk.Button(frame, text="Submit", font=("Arial", 20),
              bg="orange", fg="white", command=reset_password
              ).pack(pady=20, fill="x")
 
def create_login_window():
    global root, user_entry, pass_entry

    root = tk.Tk()
    open_fullscreen(root)
    root.title("Login System")

    set_background_image(root, "background.jpg")

    # Transparent-like center card (just black with white text)
    frame = tk.Frame(root, bg="#000000", bd=2)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(frame, text="LOGIN", font=("Arial", 40, "bold"),
             bg="#000000", fg="white").pack(pady=30)

    tk.Label(frame, text="Username", font=("Arial", 25),
             bg="#000000", fg="white").pack()
    user_entry = tk.Entry(frame, font=("Arial", 25))
    user_entry.pack(pady=5)

    tk.Label(frame, text="Password", font=("Arial", 25),
             bg="#000000", fg="white").pack()
    pass_entry = tk.Entry(frame, show="*", font=("Arial", 25))
    pass_entry.pack(pady=5)

    tk.Button(frame, text="Login", font=("Arial", 28),
              bg="#007BFF", fg="white", command=login_function
              ).pack(pady=25, fill="x")

    tk.Button(frame, text="Register", font=("Arial", 18),
              command=open_register_window).pack(pady=5, fill="x")

    tk.Button(frame, text="Forgot Password", font=("Arial", 18),
              command=open_forgot_window).pack(pady=5, fill="x")

    root.mainloop()


 
if __name__ == "__main__":
    create_login_window()
