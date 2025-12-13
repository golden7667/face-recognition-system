from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
from student import Students
import mysql.connector
import os
from train import Train 
from help import help 
from devloper import Devloper
 
 
from face_recongntion import FullscreenRecognizer
from attendance import Attendance



class FaceDetectionApp :
    def __init__(self, root):
        self.root = root
        self.root.geometry("2000x790+0+0")
        self.root.state('zoomed')    
        self.root.title("Face Detection System")

        # Image 1 
        img1 = Image.open("image/G2CM_FI454_Learn_Article_Images_[Facial_recognition]_V1a-1.webp")
        img1 = img1.resize((500, 130), Image.LANCZOS)
        self.photoimg1 = ImageTk.PhotoImage(img1)

        f_lbl1 = Label(self.root, image=self.photoimg1)
        f_lbl1.place(x=0, y=0, width=500, height=130)

        # Image 2
        img2 = Image.open("image/ggggg.jpg.webp")
        img2 = img2.resize((500, 130), Image.LANCZOS)
        self.photoimg2 = ImageTk.PhotoImage(img2)

        f_lbl2 = Label(self.root, image=self.photoimg2)
        f_lbl2.place(x=500, y=0, width=500, height=130)

        # image3
        img3 = Image.open("image/Ethical-Hacking.jpg")  
        img3 = img3.resize((500, 130), Image.LANCZOS)
        self.photoimg3 = ImageTk.PhotoImage(img3)

        f_lbl3 = Label(self.root, image=self.photoimg3)
        f_lbl3.place(x=1000, y=0, width=500, height=130)

        # Image 4 
        img4 = Image.open("image/resized_Chatobots-legal-key-issues.jpg")  
        img4 = img4.resize((500, 130), Image.LANCZOS)
        self.photoimg4 = ImageTk.PhotoImage(img4)

        f_lbl4 = Label(self.root, image=self.photoimg4)
        f_lbl4.place(x=1500, y=0, width=500, height=130)
         
         
        #bg image
        img = Image.open("image/Ethical-Hacking.jpg")  
        img = img.resize((2160, 910), Image.LANCZOS)
        self.photoimg = ImageTk.PhotoImage(img)

        f_lbl = Label(self.root, image=self.photoimg)
        f_lbl.place(x=0, y=130, width=2160, height=910)
        
        
        title_lbl = Label(self.root,
                          text="WELCOME TO MANAGEMENT SYSTEM",
                          font=("Arial", 30, "bold"),
                          fg="white",
                          bg="black")
        title_lbl.place(x=0, y=130, width=2000, height=50)
        
        
        
        #button 1
        img_btn1 = Image.open("image/studen.webp")
        img_btn1 = img_btn1.resize((200, 150), Image.LANCZOS)
        self.photo_btn1 = ImageTk.PhotoImage(img_btn1)
        def student_details(self):
          new_window = Toplevel(self.root)
          Label(new_window, text="student detail Window", 
              font=("Arial", 20)).pack(pady=20)





        #button 2
        img_btn2 = Image.open("image/istockphoto-851960058-612x612.jpg")
        img_btn2 = img_btn2.resize((200, 150), Image.LANCZOS)
        self.photo_btn2 = ImageTk.PhotoImage(img_btn2)
        
        
        
        
         #button 3
        img_btn3 = Image.open("image/att.jpg")
        img_btn3 = img_btn3.resize((200, 150), Image.LANCZOS)
        self.photo_btn3 = ImageTk.PhotoImage(img_btn3)
        
        
        #button 4
        img_btn4 = Image.open("image/resized_Chatobots-legal-key-issues.jpg")
        img_btn4 = img_btn4.resize((200, 150), Image.LANCZOS)
        self.photo_btn4 = ImageTk.PhotoImage(img_btn4)
        
        
        #button 5
        img_btn5 = Image.open("image/istockphoto-1387900612-612x612.jpg")
        img_btn5 = img_btn5.resize((200, 150), Image.LANCZOS)
        self.photo_btn5 = ImageTk.PhotoImage(img_btn5)
        
        
             
        #button 6
        img_btn6 = Image.open("image/photo.webp")
        img_btn6 = img_btn6.resize((200, 150), Image.LANCZOS)
        self.photo_btn6 = ImageTk.PhotoImage(img_btn6)
        
        
        
        #button 7
        img_btn7 = Image.open("image/devloper.webp")
        img_btn7 = img_btn7.resize((200, 150), Image.LANCZOS)
        self.photo_btn7 = ImageTk.PhotoImage(img_btn7)
        
        
        #button 8
        img_btn8 = Image.open("image/ext.jpg")
        img_btn8 = img_btn8.resize((200, 150), Image.LANCZOS)
        self.photo_btn8 = ImageTk.PhotoImage(img_btn8)
        
        
        

        # Buttons 
        self.create_button(100, 250, "Student details",  self.student_details, self.photo_btn1)
        self.create_button(450, 250, "Face detector", self.on_click_btn2, self.photo_btn2)
        self.create_button(800, 250, "Attendance", self.on_click_btn3, self.photo_btn3)
        self.create_button(1200, 250, "Help line", self.on_click_btn4, self.photo_btn4)
        self.create_button(100, 500, "Train Data", self.on_click_btn5, self.photo_btn5) 
        self.create_button(400, 500, "Photos", self.on_click_btn6, self.photo_btn6) 
        self.create_button(800, 500, "Devloper", self.on_click_btn7, self.photo_btn7)
        self.create_button(1200, 500, "EXIT", self.on_click_btn8, self.photo_btn8)
        
        
        
        
        
        
        

    # Helper to create button 
    def create_button(self, x, y, text, command, image, bg="blue"):
            b = Button(self.root, image=image, text=text, compound="top",
                   font=("Arial", 14, "bold"), fg="white", bg=bg,
                   borderwidth=3, relief=RAISED, cursor="hand2",
                   command=command)
            b.place(x=x, y=y, width=220, height=200)

        
        

    # Button Action
    
    def student_details(self):
     print("Student Details clicked!")  
     new_window = Toplevel(self.root)   
     app = Students(new_window)   
     Label(new_window, font=("Arial", 20)).pack(pady=20)
          
    def on_click_btn2(self):
        print("Face detector!")
        new_window =Toplevel(self.root)
        FullscreenRecognizer(new_window)
    
  
  

    def on_click_btn3(self):
        print(" Attendance clicked!")
        new_window =Toplevel(self.root)
        Attendance(new_window)
        
         
    def on_click_btn4(self):
            print("Help line clicked!")
            new_win = Toplevel(self.root)  # new child window
            help(new_win)   
            
    def on_click_btn5(self):
        print("Train Data clicked!")
        new_window = Toplevel(self.root)
        Train(new_window)

    def on_click_btn6(self):
     print("Photos clicked!")
     self.open_img()
     


                
    def on_click_btn7(self):
     print("Devloper clicked!")
     new_window = Toplevel(self.root)
     Devloper(new_window)
     
     
    def on_click_btn8(self):
         print("EXIT clicked!")
         self.root.destroy()
         
         
    def open_img(self):
        os.startfile("data")
         
         

         
         
        
         

         
         
     
           
             
        
        
        
        
if __name__ == "__main__":
    root = Tk()
    app = FaceDetectionApp(root)
    root.mainloop()

