from tkinter import *
from tkinter import ttk, messagebox


class help:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Detection System - Help & Chat Bot")
        self.root.geometry("900x600")
        self.root.configure(bg="white")

        
        title_lbl = Label(
            self.root,
            text="FACE DETECTION SYSTEM - HELP & CHAT BOT",
            font=("times new roman", 20, "bold"),
            bg="#0f4d7d",
            fg="white"
        )
        title_lbl.pack(side=TOP, fill=X)

        
        main_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True)

        self.help_frame = Frame(self.notebook, bg="white")
        self.chat_frame = Frame(self.notebook, bg="white")

        self.notebook.add(self.help_frame, text="Help")
        self.notebook.add(self.chat_frame, text="Chat Bot")

    
        self.help_tab_index = self.help_frame

        
        self.setup_help_tab(self.help_frame)
        self.setup_chat_tab(self.chat_frame)

    
    def setup_help_tab(self, frame):
        lbl = Label(
            frame,
            text="HELP - FACE DETECTION SYSTEM",
            font=("times new roman", 18, "bold"),
            bg="white",
            fg="#0f4d7d"
        )
        lbl.pack(anchor="w", padx=20, pady=15)

        text_frame = Frame(frame, bg="white", bd=2, relief=RIDGE)
        text_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        scroll_y = Scrollbar(text_frame, orient=VERTICAL)
        self.text_help = Text(
            text_frame,
            wrap=WORD,
            yscrollcommand=scroll_y.set,
            font=("times new roman", 13),
            bg="white",
            fg="black"
        )
        scroll_y.config(command=self.text_help.yview)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.text_help.pack(side=LEFT, fill=BOTH, expand=True)

        help_text = """
Welcome to the Face Detection System.

1. Register Face:
   • Go to 'Register / Add User' in the main window.
   • Enter user details (ID, Name, etc.).
   • Capture multiple images of the user's face.

2. Train Data:
   • Click on 'Train Data' to train the model using stored face images.
   • Wait until the training is completed.

3. Start Camera / Detection:
   • Click on 'Start Camera' or 'Face Detection'.
   • Make sure your webcam is connected and not used by another program.
   • Stand in front of the camera with good lighting.

Tips:
• Use good lighting (avoid strong backlight).
• Keep your face straight and visible.
• Make sure the camera lens is clean.

If you have issues, try restarting the application or reconnecting the camera.
"""
        self.text_help.insert(END, help_text)

    # ================= CHAT TAB =================
    def setup_chat_tab(self, frame):
        # Chat display area
        chat_log_frame = Frame(frame, bg="white", bd=2, relief=RIDGE)
        chat_log_frame.pack(fill=BOTH, expand=True, padx=20, pady=(20, 10))

        scroll_y = Scrollbar(chat_log_frame, orient=VERTICAL)
        self.chat_log = Text(
            chat_log_frame,
            wrap=WORD,
            yscrollcommand=scroll_y.set,
            font=("times new roman", 12),
            bg="white",
            fg="black",
            state=DISABLED
        )
        scroll_y.config(command=self.chat_log.yview)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.chat_log.pack(side=LEFT, fill=BOTH, expand=True)

        # Bottom input area
        bottom_frame = Frame(frame, bg="white")
        bottom_frame.pack(fill=X, padx=20, pady=(0, 20))

        self.entry_msg = Entry(
            bottom_frame,
            font=("times new roman", 12)
        )
        self.entry_msg.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))

        send_btn = Button(
            bottom_frame,
            text="Send",
            font=("times new roman", 12, "bold"),
            command=self.send_message
        )
        send_btn.pack(side=RIGHT)

        # Save chat button
        save_btn = Button(
            bottom_frame,
            text="Save Chat",
            font=("times new roman", 12),
            command=self.save_chat
        )
        save_btn.pack(side=RIGHT, padx=(0, 10))

        # Welcome message
        self.insert_chat(
            "Bot",
            "Hello! I am your help bot.\n"
            "You can ask me about: camera, register, train data, detection, error, or lighting."
        )

        # Enter key sends message
        self.entry_msg.bind("<Return>", self.send_message_event)

    # ================= HELPERS =================
    def insert_chat(self, speaker, msg):
        self.chat_log.config(state=NORMAL)
        self.chat_log.insert(END, f"{speaker}: {msg}\n")
        self.chat_log.config(state=DISABLED)
        self.chat_log.see(END)

    def save_chat(self):
        """Save whole chat to a text file."""
        self.chat_log.config(state=NORMAL)
        data = self.chat_log.get(1.0, END).strip()
        self.chat_log.config(state=DISABLED)

        if not data:
            messagebox.showinfo("Save Chat", "No chat to save.")
            return

        try:
            with open("chat_history.txt", "a", encoding="utf-8") as f:
                f.write("\n\n=== New Chat Session ===\n")
                f.write(data)
            messagebox.showinfo("Save Chat", "Chat saved to 'chat_history.txt'.")
        except Exception as e:
            messagebox.showerror("Save Chat", f"Error saving chat:\n{e}")

    def bot_reply(self, user_msg: str) -> str:
        """Simple rule-based replies using keywords."""
        msg = user_msg.lower()

        if any(w in msg for w in ["hi", "hello", "hey"]):
            return "Hello! How can I help you with the face detection system?"

        if "register" in msg or "add user" in msg:
            return (
                "To register a face:\n"
                "- Open 'Register / Add User' in the main window.\n"
                "- Enter ID, Name, and other details.\n"
                "- Capture multiple images of the face.\n"
                "- Then click 'Train Data'."
            )

        if "train" in msg or "training" in msg:
            return (
                "Train Data:\n"
                "- Make sure you have already registered faces.\n"
                "- Click 'Train Data' in the main window.\n"
                "- Wait until the training finishes.\n"
                "- After that, detection will use the new data."
            )

        if "camera" in msg or "webcam" in msg:
            return (
                "Camera help:\n"
                "- Ensure the webcam is connected.\n"
                "- Close other apps that may be using the camera.\n"
                "- In the main window, click 'Start Camera' or 'Face Detection'."
            )

        if "detect" in msg or "detection" in msg or "not working" in msg:
            return (
                "Detection tips:\n"
                "- Check that Train Data has been run.\n"
                "- Ensure your face is clearly visible.\n"
                "- Use good lighting, no strong backlight.\n"
                "- Move closer to the camera if needed."
            )

        if "error" in msg or "problem" in msg or "issue" in msg:
            return (
                "General troubleshooting:\n"
                "- Restart the application.\n"
                "- Check camera connection and drivers.\n"
                "- Ensure faces are registered and data is trained.\n"
                "- Look at the console/terminal for detailed error messages."
            )

        if "light" in msg or "dark" in msg:
            return (
                "Lighting tips:\n"
                "- Use a well-lit room with light on your face.\n"
                "- Avoid very dark rooms.\n"
                "- Avoid bright light directly behind you."
            )

        if "thank" in msg or "thanks" in msg:
            return "You're welcome! 😊 If you have more questions, just ask."

        return (
            "I didn't understand that.\n"
            "Try asking about: camera, register, train data, detection, error, or lighting."
        )

    def send_message(self):
        msg = self.entry_msg.get().strip()
        if not msg:
            return

        
        self.insert_chat("You", msg)

        
        reply = self.bot_reply(msg)
        self.insert_chat("Bot", reply)

    
        if any(word in msg.lower() for word in ["camera", "register", "train", "detection", "help"]):
            self.notebook.select(self.help_tab_index)

        
        self.entry_msg.delete(0, END)

    def send_message_event(self, event):
        self.send_message()


if __name__ == "__main__":
    root = Tk()
    app = help(root)
    root.mainloop()
