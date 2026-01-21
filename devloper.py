from tkinter import *
from PIL import Image, ImageTk
import webbrowser 
import os


class Devloper:
    def __init__(self, root):
        self.root = root
        self.root.state('zoomed')   
        self.root.title("Developer")

        # TITLE 
        title_lbl = Label(
            self.root,
            text="DEVELOPER",
            font=("times new roman", 30, "bold"),
            bg="darkblue",
            fg="white"
        )
        title_lbl.pack(side=TOP, fill=X)

        # MAIN FRAME 
        main_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        main_frame.place(x=20, y=80, width=self.root.winfo_screenwidth()-40, height=self.root.winfo_screenheight()-120)

        # Name
        name_lbl = Label(
            main_frame,
            text="Name : Golden Kumar",
            font=("times new roman", 22, "bold"),
            bg="white",
            anchor="w"
        )
        name_lbl.place(x=20, y=20)

        # Role
        role_lbl = Label(
            main_frame,
            text="Role   : Python Developer | ML Enthusiast",
            font=("times new roman", 18),
            bg="white",
            anchor="w"
        )
        role_lbl.place(x=20, y=70)

        # Project
        project_lbl = Label(
            main_frame,
            text="Project: Face Recognition Attendance System",
            font=("times new roman", 18),
            bg="white",
            anchor="w"
        )
        project_lbl.place(x=20, y=110)

        # About
        about_text = (
            "About:\n"
            "I am a passionate Python developer interested in Computer Vision\n"
            "and Machine Learning. This project is built using OpenCV, Tkinter,\n"
            "and MySQL to create an automated attendance system using\n"
            "face recognition. I enjoy building end-to-end applications and\n"
            "learning new technologies."
        )

        about_lbl = Label(
            main_frame,
            text=about_text,
            font=("times new roman", 16),
            bg="white",
            justify=LEFT,
            anchor="nw"
        )
        about_lbl.place(x=20, y=160)

        
        contact_lbl = Label(
            main_frame,
            text="Contact:",
            font=("times new roman", 18, "bold"),
            bg="white",
            anchor="w"
        )
        contact_lbl.place(x=20, y=298)

        email_lbl = Label(
            main_frame,
            text="Email   : goldenkrsingh921@gmail.com",
            font=("times new roman", 16),
            bg="white",
            anchor="w"
        )
        email_lbl.place(x=40, y=330)

        phone_lbl = Label(
            main_frame,
            text="Mobile : +91-7667711403",
            font=("times new roman", 16),
            bg="white",
            anchor="w"
        )
        phone_lbl.place(x=40, y=360)

        # SOCIAL LINKS
                # SOCIAL LINKS
        def open_github():
            webbrowser.open_new("https://github.com/golden2804")

        def open_linkedin():
            webbrowser.open_new("https://www.linkedin.com/in/golden-kumar-891567246/")

        def open_instagram():
            webbrowser.open_new("https://www.instagram.com/its_ethic_gdk/")


        def open_portfolio():
            webbrowser.open_new("https://your-portfolio-site.com")

        btn_style = {
            "font": ("times new roman", 14, "bold"),
            "bg": "darkblue",
            "fg": "white",
            "cursor": "hand2",
            "bd": 1,
            "relief": RIDGE
        }

        github_btn = Button(main_frame, text="GitHub", command=open_github, **btn_style)
        github_btn.place(x=20, y=420, width=100, height=35)

        linkedin_btn = Button(main_frame, text="LinkedIn", command=open_linkedin, **btn_style)
        linkedin_btn.place(x=140, y=420, width=100, height=35)

        instagram_btn = Button(main_frame, text="Instagram", command=open_instagram, **btn_style)
        instagram_btn.place(x=260, y=420, width=120, height=35)

        portfolio_btn = Button(main_frame, text="Portfolio", command=open_portfolio, **btn_style)
        portfolio_btn.place(x=400, y=420, width=120, height=35)

                
        img = Image.open("image\devloper\IMG_0157 (1).jpg")
        img = img.resize((450, 450), Image.LANCZOS)
        self.photo_dev = ImageTk.PhotoImage(img)

        img_lbl = Label(main_frame, image=self.photo_dev, bg="white", bd=2, relief=RIDGE)
        img_lbl.place(x=900, y=80, width=450, height=450)

        img_lbl.image = self.photo_dev    



if __name__ == "__main__":
    root = Tk()
    app = Devloper(root)
    root.mainloop()
