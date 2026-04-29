# election_commission_fixed.py - Fixed Admin Color + Face Matching Threshold
import tkinter as tk
from tkinter import ttk, messagebox, font
import sqlite3
from datetime import datetime
import cv2
import face_recognition
import numpy as np
from PIL import Image, ImageTk
import os
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

class ElectionCommissionSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Election Commission - Voter Verification System")
        self.root.geometry("1300x800")
        
        self.current_user = None
        self.current_role = None
        self.selected_role = None
        
        # Camera variables
        self.camera = None
        self.is_capturing = False
        self.auto_capture_after_detection = False
        
        # Face matching threshold (lower = stricter)
        self.face_match_threshold = 0.5  # 0.5 is stricter than default 0.6
        
        # Colors - Added 'info' color
        self.colors = {
            'primary': '#1B4F72', 'secondary': '#3498DB', 'success': '#27AE60',
            'danger': '#E74C3C', 'warning': '#F39C12', 'light': '#ECF0F1',
            'white': '#FFFFFF', 'gray': '#95A5A6', 'orange': '#E67E22', 
            'purple': '#9B59B6', 'info': '#1ABC9C'  # Added 'info' color
        }
        
        # Fonts
        self.title_font = font.Font(family='Segoe UI', size=20, weight='bold')
        self.heading_font = font.Font(family='Segoe UI', size=14, weight='bold')
        self.normal_font = font.Font(family='Segoe UI', size=10)
        self.button_font = font.Font(family='Segoe UI', size=10, weight='bold')
        
        # Setup database
        self.setup_database()
        
        self.center_window()
        self.show_role_selection()
        self.root.mainloop()
    
    def center_window(self):
        self.root.update_idletasks()
        width = 1300
        height = 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_database(self):
        """Initialize database with all required tables"""
        self.conn = sqlite3.connect('voting_system.db')
        self.cursor = self.conn.cursor()
        
        # Check and add columns
        self.cursor.execute("PRAGMA table_info(voters)")
        columns = [col[1] for col in self.cursor.fetchall()]
        
        # Voters table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS voters (
            voter_id VARCHAR(20) PRIMARY KEY,
            aadhaar_id VARCHAR(12) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            father_name VARCHAR(100),
            age INTEGER,
            gender VARCHAR(10),
            address TEXT,
            phone_number VARCHAR(15),
            constituency_name VARCHAR(100),
            registered_date TIMESTAMP,
            voted INTEGER DEFAULT 0,
            verified_at TIMESTAMP NULL,
            verified_by VARCHAR(50) NULL
        )''')
        
        if 'face_encoding' not in columns:
            self.cursor.execute("ALTER TABLE voters ADD COLUMN face_encoding BLOB")
        
        if 'fingerprint_template' not in columns:
            self.cursor.execute("ALTER TABLE voters ADD COLUMN fingerprint_template BLOB")
        
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # System logs table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username VARCHAR(50),
            role VARCHAR(20),
            action VARCHAR(50),
            details TEXT
        )''')
        
        # Insert default users
        self.cursor.execute("SELECT COUNT(*) FROM users")
        if self.cursor.fetchone()[0] == 0:
            default_users = [
                ('admin', 'admin123', 'System Administrator', 'admin'),
                ('registrar', 'registrar123', 'Registration Officer', 'registrar'),
                ('verifier', 'verifier123', 'Verification Officer', 'verifier')
            ]
            for username, password, full_name, role in default_users:
                self.cursor.execute(
                    "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                    (username, password, full_name, role)
                )
        
        # Insert sample voters if empty
        self.cursor.execute("SELECT COUNT(*) FROM voters")
        if self.cursor.fetchone()[0] == 0:
            sample_voters = [
                ('VOTER001', '123456789012', 'Rajesh Kumar', 'Suresh Kumar', 42, 'M', 
                 '123 Gandhi Nagar, New Delhi', '9876543210', 'New Delhi North'),
                ('VOTER002', '234567890123', 'Priya Sharma', 'Ramesh Sharma', 35, 'F',
                 '456 Lajpat Nagar, New Delhi', '9876543211', 'New Delhi East'),
                ('VOTER003', '345678901234', 'Amit Patel', 'Rajesh Patel', 28, 'M',
                 '789 Civil Lines, Ahmedabad', '9876543212', 'Ahmedabad West'),
            ]
            for voter in sample_voters:
                self.cursor.execute('''INSERT INTO voters 
                    (voter_id, aadhaar_id, name, father_name, age, gender, address, phone_number, constituency_name, registered_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (*voter, datetime.now()))
        
        self.conn.commit()
    
    def log_action(self, action, details):
        try:
            if self.current_user:
                self.cursor.execute(
                    "INSERT INTO logs (username, role, action, details) VALUES (?, ?, ?, ?)",
                    (self.current_user, self.current_role, action, details)
                )
                self.conn.commit()
        except Exception as e:
            pass
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_role_selection(self):
        self.clear_window()
        bg_frame = tk.Frame(self.root, bg=self.colors['light'])
        bg_frame.pack(fill='both', expand=True)
        
        center_frame = tk.Frame(bg_frame, bg=self.colors['light'])
        center_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(center_frame, text="🗳️", font=('Segoe UI', 48), 
                bg=self.colors['light']).pack(pady=10)
        tk.Label(center_frame, text="Election Commission", font=self.title_font, 
                bg=self.colors['light'], fg=self.colors['primary']).pack()
        tk.Label(center_frame, text="Biometric Voter Verification System", font=self.heading_font, 
                bg=self.colors['light'], fg=self.colors['gray']).pack(pady=(5, 20))
        
        button_frame = tk.Frame(center_frame, bg=self.colors['light'])
        button_frame.pack()
        
        tk.Button(button_frame, text="👑 ADMIN", 
                 command=lambda: self.show_login('admin'),
                 font=self.button_font, bg=self.colors['primary'], fg='white',
                 relief='flat', padx=40, pady=12, width=15, cursor='hand2').pack(pady=8)
        
        tk.Button(button_frame, text="📝 REGISTRAR", 
                 command=lambda: self.show_login('registrar'),
                 font=self.button_font, bg=self.colors['purple'], fg='white',
                 relief='flat', padx=40, pady=12, width=15, cursor='hand2').pack(pady=8)
        
        tk.Button(button_frame, text="🔍 VERIFIER", 
                 command=lambda: self.show_login('verifier'),
                 font=self.button_font, bg=self.colors['orange'], fg='white',
                 relief='flat', padx=40, pady=12, width=15, cursor='hand2').pack(pady=8)
        
        tk.Button(button_frame, text="Exit", command=self.root.quit,
                 font=self.normal_font, bg=self.colors['danger'], fg='white',
                 relief='flat', padx=40, pady=8, width=15, cursor='hand2').pack(pady=15)
    
    def show_login(self, role):
        self.clear_window()
        self.selected_role = role
        
        role_colors = {'admin': self.colors['primary'], 'registrar': self.colors['purple'], 'verifier': self.colors['orange']}
        role_icons = {'admin': '👑', 'registrar': '📝', 'verifier': '🔍'}
        role_names = {'admin': 'Administrator', 'registrar': 'Registrar', 'verifier': 'Verifier'}
        
        bg_frame = tk.Frame(self.root, bg=self.colors['light'])
        bg_frame.pack(fill='both', expand=True)
        
        center_frame = tk.Frame(bg_frame, bg=self.colors['light'])
        center_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        login_card = tk.Frame(center_frame, bg=self.colors['white'], relief='flat', bd=0)
        login_card.pack(padx=40, pady=40)
        
        tk.Label(login_card, text=role_icons[role], font=('Segoe UI', 40), 
                bg=self.colors['white']).pack(pady=10)
        tk.Label(login_card, text=f"{role_names[role]} Login", font=self.heading_font, 
                bg=self.colors['white'], fg=role_colors[role]).pack()
        
        form_frame = tk.Frame(login_card, bg=self.colors['white'])
        form_frame.pack(padx=30, pady=20)
        
        tk.Label(form_frame, text="Username", font=self.normal_font, bg=self.colors['white']).pack(anchor='w')
        self.login_username = tk.Entry(form_frame, font=self.normal_font, width=25, relief='solid', bd=1)
        self.login_username.pack(pady=(0, 12), ipady=6)
        
        tk.Label(form_frame, text="Password", font=self.normal_font, bg=self.colors['white']).pack(anchor='w')
        self.login_password = tk.Entry(form_frame, font=self.normal_font, width=25, show='*', relief='solid', bd=1)
        self.login_password.pack(pady=(0, 18), ipady=6)
        
        default_pass = {'admin': 'admin123', 'registrar': 'registrar123', 'verifier': 'verifier123'}
        tk.Label(login_card, text=f"Default: {role} / {default_pass[role]}", 
                font=('Segoe UI', 8), bg=self.colors['white'], fg=self.colors['gray']).pack()
        
        tk.Button(login_card, text="Login", command=self.do_login,
                 font=self.button_font, bg=role_colors[role], fg='white',
                 relief='flat', padx=40, pady=10, cursor='hand2').pack(pady=15)
        
        tk.Button(login_card, text="← Back", command=self.show_role_selection,
                 font=self.normal_font, bg=self.colors['gray'], fg='white',
                 relief='flat', padx=20, pady=5, cursor='hand2').pack()
        
        self.login_password.bind('<Return>', lambda e: self.do_login())
        self.login_username.bind('<Return>', lambda e: self.do_login())
    
    def do_login(self):
        username = self.login_username.get().strip()
        password = self.login_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Login Failed", "Please enter both username and password!")
            return
        
        try:
            self.cursor.execute(
                "SELECT * FROM users WHERE username=? AND password_hash=? AND role=?",
                (username, password, self.selected_role)
            )
            user = self.cursor.fetchone()
            
            if user:
                self.current_user = username
                self.current_role = self.selected_role
                self.log_action("Login", "User logged in successfully")
                
                if self.current_role == 'admin':
                    self.show_admin_dashboard()
                elif self.current_role == 'registrar':
                    self.show_registration_form()
                elif self.current_role == 'verifier':
                    self.show_verifier_dashboard()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password!")
        except Exception as e:
            messagebox.showerror("Error", f"Login error: {str(e)}")
    
    def create_header(self, title):
        role_colors = {'admin': self.colors['primary'], 'registrar': self.colors['purple'], 'verifier': self.colors['orange']}
        header = tk.Frame(self.root, bg=role_colors[self.current_role], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text=title, font=self.title_font,
                bg=role_colors[self.current_role], fg=self.colors['white']).pack(side='left', padx=20, pady=10)
        
        tk.Button(header, text="Logout", command=self.logout,
                 font=self.normal_font, bg=self.colors['danger'], fg='white',
                 relief='flat', padx=15, pady=3, cursor='hand2').pack(side='right', padx=20)
        
        tk.Label(header, text=f"{self.current_user} ({self.current_role})", 
                font=self.normal_font, bg=role_colors[self.current_role], fg=self.colors['light']).pack(side='right')
    
    def logout(self):
        self.stop_camera()
        self.log_action("Logout", "User logged out")
        self.current_user = None
        self.current_role = None
        self.selected_role = None
        self.show_role_selection()
    
    def stop_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
        self.is_capturing = False
    
    # ==================== REGISTRAR MODULE ====================
    
    def show_registration_form(self):
        self.clear_window()
        self.create_header("Register New Voter - Face Capture")
        
        main_frame = tk.Frame(self.root, bg=self.colors['light'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left side - Form
        form_frame = tk.LabelFrame(main_frame, text="Voter Details", font=self.heading_font, bg='white')
        form_frame.pack(side='left', fill='both', expand=True, padx=10)
        
        fields = [
            ("Voter ID:", "voter_id"), ("Aadhaar (12 digits):", "aadhaar_id"),
            ("Full Name:", "name"), ("Father's Name:", "father_name"),
            ("Age:", "age"), ("Gender:", "gender"), ("Phone:", "phone"),
            ("Address:", "address"), ("Constituency:", "constituency")
        ]
        
        self.form_entries = {}
        
        for i, (label, key) in enumerate(fields):
            frame = tk.Frame(form_frame, bg='white')
            frame.pack(fill='x', padx=15, pady=3)
            tk.Label(frame, text=label, font=self.normal_font, bg='white', width=15, anchor='w').pack(side='left')
            
            if key == 'gender':
                self.form_entries[key] = ttk.Combobox(frame, values=['Male', 'Female', 'Other'], 
                                                      font=self.normal_font, state='readonly', width=27)
                self.form_entries[key].set('Male')
                self.form_entries[key].pack(side='left', padx=5, fill='x', expand=True)
            elif key == 'address':
                self.form_entries[key] = tk.Text(frame, font=self.normal_font, height=2, width=27)
                self.form_entries[key].pack(side='left', padx=5, fill='x', expand=True)
            else:
                self.form_entries[key] = tk.Entry(frame, font=self.normal_font, width=27)
                self.form_entries[key].pack(side='left', padx=5, fill='x', expand=True)
        
        # Right side - Camera
        cam_frame = tk.LabelFrame(main_frame, text="Face Capture", font=self.heading_font, bg='white')
        cam_frame.pack(side='right', fill='both', padx=10, ipadx=20)
        
        self.video_label = tk.Label(cam_frame, bg='black', width=50, height=25)
        self.video_label.pack(pady=10, padx=10)
        
        self.face_status = tk.Label(cam_frame, text="❌ Face Not Captured", font=self.normal_font, fg='red', bg='white')
        self.face_status.pack(pady=5)
        
        self.capture_btn = tk.Button(cam_frame, text="📸 Start Camera", command=self.start_face_capture,
                                     font=self.button_font, bg=self.colors['purple'], fg='white',
                                     relief='flat', padx=20, pady=8, cursor='hand2', width=20)
        self.capture_btn.pack(pady=5)
        
        self.face_preview_label = tk.Label(cam_frame, text="Preview will appear here", 
                                           bg='lightgray', width=50, height=10)
        self.face_preview_label.pack(pady=10, padx=10)
        
        self.face_encoding = None
        
        button_frame = tk.Frame(main_frame, bg=self.colors['light'])
        button_frame.pack(side='bottom', fill='x', pady=20)
        
        tk.Button(button_frame, text="💾 Register Voter", command=self.save_voter_with_face,
                 font=self.button_font, bg=self.colors['success'], fg='white',
                 relief='flat', padx=30, pady=10, cursor='hand2').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=self.go_back,
                 font=self.button_font, bg=self.colors['gray'], fg='white',
                 relief='flat', padx=30, pady=10, cursor='hand2').pack(side='left', padx=10)
    
    def start_face_capture(self):
        self.camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if self.camera.isOpened():
            self.is_capturing = True
            self.capture_btn.config(state='disabled', text="📸 Looking for face...")
            self.update_video_feed()
    
    def update_video_feed(self):
        if not self.is_capturing:
            return
        
        ret, frame = self.camera.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            display_frame = frame.copy()
            if face_locations:
                for (top, right, bottom, left) in face_locations:
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Auto capture on face detection
                if not self.face_encoding:
                    self.face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0].tobytes()
                    self.face_status.config(text="✅ Face Captured Successfully!", fg='green')
                    self.capture_btn.config(text="✅ Face Captured!")
                    
                    # Show preview
                    preview = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                    preview_img = Image.fromarray(preview)
                    preview_img = preview_img.resize((300, 200))
                    preview_photo = ImageTk.PhotoImage(preview_img)
                    self.face_preview_label.config(image=preview_photo, text="")
                    self.face_preview_label.image = preview_photo
                    
                    self.is_capturing = False
                    self.camera.release()
                    return
            
            # Display live feed
            img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            img = img.resize((400, 300))
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)
        
        if self.is_capturing:
            self.root.after(50, self.update_video_feed)
    
    def save_voter_with_face(self):
        try:
            voter_id = self.form_entries['voter_id'].get().strip()
            aadhaar_id = self.form_entries['aadhaar_id'].get().strip()
            name = self.form_entries['name'].get().strip()
            father_name = self.form_entries['father_name'].get().strip()
            age = self.form_entries['age'].get().strip()
            gender = self.form_entries['gender'].get()
            phone = self.form_entries['phone'].get().strip()
            address = self.form_entries['address'].get('1.0', 'end').strip()
            constituency = self.form_entries['constituency'].get().strip()
            
            if not all([voter_id, aadhaar_id, name]):
                messagebox.showerror("Error", "Voter ID, Aadhaar, and Name are required!")
                return
            
            if len(aadhaar_id) != 12 or not aadhaar_id.isdigit():
                messagebox.showerror("Error", "Aadhaar must be 12 digits!")
                return
            
            if not self.face_encoding:
                messagebox.showerror("Error", "Please capture face first!")
                return
            
            self.cursor.execute("SELECT voter_id FROM voters WHERE voter_id=? OR aadhaar_id=?", (voter_id, aadhaar_id))
            if self.cursor.fetchone():
                messagebox.showerror("Error", "Voter ID or Aadhaar already exists!")
                return
            
            self.cursor.execute('''INSERT INTO voters 
                (voter_id, aadhaar_id, name, father_name, age, gender, address, phone_number, 
                 constituency_name, face_encoding, registered_date, voted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (voter_id, aadhaar_id, name, father_name, age if age else None, 
                 gender, address, phone, constituency, self.face_encoding, datetime.now(), 0))
            
            self.conn.commit()
            self.log_action("Voter Registration", f"Registered {name} ({voter_id})")
            
            messagebox.showinfo("Success", f"Voter {name} registered successfully!")
            self.go_back()
            
        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {str(e)}")
    
    # ==================== VERIFIER MODULE WITH STRICT FACE MATCHING ====================
    
    def show_verifier_dashboard(self):
        self.clear_window()
        self.create_header("Verifier Dashboard - 2 Step Verification")
        
        main_container = tk.Frame(self.root, bg=self.colors['light'])
        main_container.pack(fill='both', expand=True)
        
        # Stats frame
        self.stats_frame = tk.Frame(main_container, bg=self.colors['light'])
        self.stats_frame.pack(fill='x', pady=10, padx=20)
        self.update_stats()
        
        # Search frame
        search_frame = tk.LabelFrame(main_container, text="🔍 STEP 1: SEARCH VOTER", font=self.heading_font, bg='white')
        search_frame.pack(fill='x', pady=10, padx=20)
        
        search_inner = tk.Frame(search_frame, bg='white')
        search_inner.pack(pady=15, padx=15)
        
        tk.Label(search_inner, text="Enter Voter ID or Aadhaar Number:", font=self.normal_font, bg='white').pack()
        
        self.verify_search_entry = tk.Entry(search_inner, font=self.normal_font, width=40)
        self.verify_search_entry.pack(pady=10)
        self.verify_search_entry.bind('<Return>', lambda e: self.verifier_search_voter())
        
        tk.Button(search_inner, text="🔍 SEARCH VOTER", command=self.verifier_search_voter,
                 font=self.button_font, bg=self.colors['orange'], fg='white',
                 relief='flat', padx=30, pady=8, cursor='hand2').pack()
        
        # Results area
        results_container = tk.Frame(main_container, bg=self.colors['light'])
        results_container.pack(fill='both', expand=True, pady=10, padx=20)
        
        self.canvas = tk.Canvas(results_container, bg=self.colors['light'], highlightthickness=0)
        scrollbar = tk.Scrollbar(results_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors['light'])
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.verify_results_frame = self.scrollable_frame
    
    def update_stats(self):
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        self.cursor.execute("SELECT COUNT(*) FROM voters WHERE voted=0")
        pending = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM voters WHERE voted=1")
        verified = self.cursor.fetchone()[0]
        
        stats = [
            ("⏳ PENDING VERIFICATION", pending, self.colors['warning']),
            ("✅ VERIFIED", verified, self.colors['success']),
        ]
        
        for i, (label, value, color) in enumerate(stats):
            card = tk.Frame(self.stats_frame, bg='white', relief='flat', bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            self.stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=self.normal_font, bg='white', fg=color).pack(pady=(10, 2))
            tk.Label(card, text=str(value), font=('Segoe UI', 28, 'bold'), bg='white', fg=color).pack(pady=(2, 10))
    
    def verifier_search_voter(self):
        search_term = self.verify_search_entry.get().strip()
        
        if not search_term:
            messagebox.showerror("Error", "Please enter Voter ID or Aadhaar!")
            return
        
        for widget in self.verify_results_frame.winfo_children():
            widget.destroy()
        
        self.cursor.execute('''SELECT voter_id, aadhaar_id, name, father_name, age, gender, 
                               address, phone_number, constituency_name, voted, face_encoding
                               FROM voters WHERE voter_id=? OR aadhaar_id=?''', 
                            (search_term, search_term))
        voter = self.cursor.fetchone()
        
        if not voter:
            tk.Label(self.verify_results_frame, text="❌ VOTER NOT FOUND!", 
                    font=self.heading_font, fg='red', bg=self.colors['light']).pack(pady=50)
            return
        
        self.verified_voter = {
            'voter_id': voter[0],
            'aadhaar_id': voter[1],
            'name': voter[2],
            'father_name': voter[3],
            'age': voter[4],
            'gender': voter[5],
            'address': voter[6],
            'phone': voter[7],
            'constituency': voter[8],
            'voted': voter[9],
            'face_encoding': voter[10]
        }
        
        self.display_verifier_details()
    
    def display_verifier_details(self):
        voter = self.verified_voter
        
        if voter['voted']:
            tk.Label(self.verify_results_frame, text="⚠️ THIS VOTER HAS ALREADY BEEN VERIFIED!", 
                    font=self.heading_font, fg='red', bg=self.colors['light']).pack(pady=30)
            return
        
        main_card = tk.Frame(self.verify_results_frame, bg='white', relief='flat', bd=2)
        main_card.pack(fill='both', expand=True, pady=5)
        
        tk.Label(main_card, text="✅ VOTER DETAILS", font=self.heading_font, 
                bg=self.colors['success'], fg='white', pady=10).pack(fill='x')
        
        details_frame = tk.Frame(main_card, bg='white')
        details_frame.pack(padx=25, pady=15, fill='both', expand=True)
        
        details = [
            ("🗳️ Voter ID:", voter['voter_id']),
            ("🆔 Aadhaar:", f"XXXX-XXXX-{voter['aadhaar_id'][-4:]}"),
            ("👤 Name:", voter['name']),
            ("👨 Father's Name:", voter['father_name'] or "N/A"),
            ("📅 Age:", str(voter['age']) if voter['age'] else "N/A"),
            ("⚥ Gender:", voter['gender'] or "N/A"),
            ("📞 Phone:", voter['phone'] or "N/A"),
            ("🗺️ Constituency:", voter['constituency'] or "N/A")
        ]
        
        for i, (label, value) in enumerate(details):
            frame = tk.Frame(details_frame, bg='white')
            frame.pack(fill='x', pady=6)
            tk.Label(frame, text=label, font=('Segoe UI', 11, 'bold'), 
                    bg='white', width=14, anchor='w').pack(side='left')
            tk.Label(frame, text=value, font=('Segoe UI', 11), 
                    bg='white', anchor='w', wraplength=550, justify='left').pack(side='left', padx=5)
        
        # Address
        addr_frame = tk.Frame(details_frame, bg='white')
        addr_frame.pack(fill='x', pady=6)
        tk.Label(addr_frame, text="📍 Address:", font=('Segoe UI', 11, 'bold'), 
                bg='white', width=14, anchor='w').pack(side='left')
        tk.Label(addr_frame, text=voter['address'] or "N/A", font=('Segoe UI', 11), 
                bg='white', anchor='w', wraplength=550, justify='left').pack(side='left', padx=5)
        
        # Face Status
        status_text = "✅ Face Enrolled" if voter['face_encoding'] else "⚠️ No Face Data"
        status_color = 'green' if voter['face_encoding'] else 'orange'
        tk.Label(details_frame, text=f"Face Status: {status_text}", 
                font=('Segoe UI', 11, 'bold'), fg=status_color, bg='white').pack(anchor='w', pady=10)
        
        # VERIFY BUTTON
        button_frame = tk.Frame(main_card, bg='white')
        button_frame.pack(fill='x', pady=25, padx=25)
        
        if voter['face_encoding']:
            verify_btn = tk.Button(button_frame, 
                                   text="🔐 START 2-STEP VERIFICATION (Aadhaar → Face)", 
                                   command=self.start_2step_verification,
                                   font=('Segoe UI', 14, 'bold'), 
                                   bg=self.colors['success'], fg='white',
                                   relief='raised', padx=50, pady=15, cursor='hand2')
            verify_btn.pack(fill='x')
            tk.Label(button_frame, text="Click to begin verification process", 
                    font=self.normal_font, fg=self.colors['gray'], bg='white').pack(pady=5)
        else:
            tk.Label(button_frame, text="❌ Cannot verify: No face data available. Please register with face first.", 
                    font=self.heading_font, fg='red', bg='white').pack(pady=10)
        
        self.canvas.yview_moveto(1.0)
    
    def start_2step_verification(self):
        self.aadhaar_verification()
    
    def aadhaar_verification(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Step 1/2: Aadhaar Verification")
        dialog.geometry("550x400")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (550 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f'550x400+{x}+{y}')
        
        tk.Label(dialog, text="🔐 STEP 1 OF 2", font=self.heading_font, 
                bg='white', fg=self.colors['orange']).pack(pady=15)
        tk.Label(dialog, text="Aadhaar Verification", font=self.title_font, 
                bg='white', fg=self.colors['primary']).pack()
        tk.Label(dialog, text=f"Verifying for: {self.verified_voter['name']}", 
                font=self.normal_font, bg='white').pack(pady=15)
        tk.Label(dialog, text="Enter 12-digit Aadhaar number:", 
                font=self.normal_font, bg='white').pack()
        
        aadhaar_entry = tk.Entry(dialog, font=self.normal_font, width=25, justify='center')
        aadhaar_entry.pack(pady=12)
        
        status_label = tk.Label(dialog, text="", font=self.normal_font, bg='white')
        status_label.pack()
        
        def verify():
            entered = aadhaar_entry.get().strip()
            if entered == self.verified_voter['aadhaar_id']:
                status_label.config(text="✅ Aadhaar verified!", fg='green')
                dialog.destroy()
                self.face_verification()
            else:
                status_label.config(text="❌ Aadhaar does not match!", fg='red')
                aadhaar_entry.delete(0, tk.END)
        
        tk.Button(dialog, text="Verify Aadhaar", command=verify,
                 font=self.button_font, bg=self.colors['success'], fg='white',
                 relief='flat', padx=35, pady=10, cursor='hand2').pack(pady=15)
        tk.Button(dialog, text="Cancel", command=dialog.destroy,
                 font=self.normal_font, bg=self.colors['gray'], fg='white',
                 relief='flat', padx=25, pady=6, cursor='hand2').pack()
        
        aadhaar_entry.bind('<Return>', lambda e: verify())
        aadhaar_entry.focus()
    
    def face_verification(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Step 2/2: Face Verification")
        dialog.geometry("900x750")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (dialog.winfo_screenheight() // 2) - (750 // 2)
        dialog.geometry(f'900x750+{x}+{y}')
        
        tk.Label(dialog, text="🔐 STEP 2 OF 2", font=self.heading_font, 
                bg='white', fg=self.colors['orange']).pack(pady=15)
        tk.Label(dialog, text="Face Verification", font=self.title_font, 
                bg='white', fg=self.colors['primary']).pack()
        tk.Label(dialog, text=f"Verifying for: {self.verified_voter['name']}", 
                font=self.normal_font, bg='white').pack(pady=10)
        tk.Label(dialog, text="IMPORTANT: Make sure YOU are the registered voter!", 
                font=self.normal_font, fg='red', bg='white').pack()
        
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
        
        video_label = tk.Label(dialog, bg='black', width=85, height=40)
        video_label.pack(pady=15)
        
        status_label = tk.Label(dialog, text="Click 'Start Face Scan' and look at camera", 
                                font=self.normal_font, fg='blue', bg='white')
        status_label.pack(pady=5)
        
        def update_feed():
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    display_frame = frame.copy()
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_frame)
                    
                    if face_locations:
                        for (top, right, bottom, left) in face_locations:
                            cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                    
                    img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
                    img = img.resize((800, 550))
                    imgtk = ImageTk.PhotoImage(image=img)
                    video_label.imgtk = imgtk
                    video_label.config(image=imgtk)
            dialog.after(50, update_feed)
        
        update_feed()
        
        def verify_face():
            status_label.config(text="📸 Capturing face... Analyzing...", fg='orange')
            dialog.update()
            
            ret, frame = cap.read()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if not face_locations:
                    status_label.config(text="❌ No face detected! Please look at camera directly.", fg='red')
                    return
                
                live_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if not live_encodings:
                    status_label.config(text="❌ Could not encode face! Try better lighting.", fg='red')
                    return
                
                stored_encoding = np.frombuffer(self.verified_voter['face_encoding'], dtype=np.float64)
                
                # Calculate face distance (lower = better match)
                face_distances = face_recognition.face_distance([stored_encoding], live_encodings[0])
                distance = face_distances[0]
                
                # Use threshold for strict matching
                if distance < self.face_match_threshold:
                    # Face matches successfully
                    status_label.config(text=f"✅ Face Verified! (Confidence: {(1-distance)*100:.1f}%)", fg='green')
                    dialog.update()
                    
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.cursor.execute(
                        "UPDATE voters SET voted=1, verified_at=?, verified_by=? WHERE voter_id=?",
                        (current_time, self.current_user, self.verified_voter['voter_id'])
                    )
                    self.conn.commit()
                    self.log_action("Voter Verification", f"Verified voter {self.verified_voter['voter_id']}")
                    
                    messagebox.showinfo("Success!", f"✅ {self.verified_voter['name']} marked as VOTED!\n\nFace match confidence: {(1-distance)*100:.1f}%")
                    cap.release()
                    dialog.destroy()
                    
                    # Auto refresh
                    self.verify_search_entry.delete(0, tk.END)
                    for widget in self.verify_results_frame.winfo_children():
                        widget.destroy()
                    self.update_stats()
                    tk.Label(self.verify_results_frame, 
                            text=f"✅ SUCCESS! {self.verified_voter['name']} has been marked as VOTED!", 
                            font=self.heading_font, fg='green', bg=self.colors['light']).pack(pady=50)
                    
                else:
                    # Face does not match
                    status_label.config(text=f"❌ Face does NOT match registered voter! (Match: {(1-distance)*100:.1f}% < 50%)", fg='red')
            else:
                status_label.config(text="❌ Failed to capture image!", fg='red')
        
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="📸 START FACE SCAN", command=verify_face,
                 font=self.button_font, bg=self.colors['success'], fg='white',
                 relief='raised', padx=50, pady=15, cursor='hand2').pack(side='left', padx=15)
        
        tk.Button(btn_frame, text="Cancel", command=lambda: self.cleanup_camera(cap, dialog),
                 font=self.button_font, bg=self.colors['gray'], fg='white',
                 relief='flat', padx=30, pady=15, cursor='hand2').pack(side='left', padx=15)
    
    def cleanup_camera(self, cap, dialog):
        cap.release()
        dialog.destroy()
    
    # ==================== ADMIN DASHBOARD ====================
    
    def show_admin_dashboard(self):
        self.clear_window()
        self.create_header("Admin Dashboard")
        
        # Statistics
        self.cursor.execute("SELECT COUNT(*) FROM voters")
        total = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM voters WHERE voted=1")
        voted = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM voters WHERE face_encoding IS NOT NULL")
        face_enrolled = self.cursor.fetchone()[0]
        
        stats_frame = tk.Frame(self.root, bg=self.colors['light'])
        stats_frame.pack(fill='x', padx=20, pady=20)
        
        # Using 'secondary' instead of 'info' to avoid any issues
        stats = [
            ("Total Voters", total, self.colors['secondary'], "👥"),
            ("Voted", voted, self.colors['success'], "✅"),
            ("Face Enrolled", face_enrolled, self.colors['secondary'], "📸"),
            ("Remaining", total - voted, self.colors['warning'], "⏳")
        ]
        
        for i, (label, value, color, icon) in enumerate(stats):
            card = tk.Frame(stats_frame, bg='white', relief='flat', bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=icon, font=('Segoe UI', 28), bg='white').pack(pady=(10, 2))
            tk.Label(card, text=str(value), font=('Segoe UI', 24, 'bold'), bg='white', fg=color).pack()
            tk.Label(card, text=label, font=self.normal_font, bg='white', fg=self.colors['gray']).pack(pady=(2, 10))
        
        menu_frame = tk.Frame(self.root, bg=self.colors['light'])
        menu_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        admin_menus = [
            ("📝 Register Voter", "Face enrollment", self.show_registration_form),
            ("🔍 Verify Voter", "2-Step verification", self.show_verifier_dashboard),
            ("📊 Reports", "View statistics", self.show_reports),
            ("📋 Voter List", "View all voters", self.show_voter_list),
        ]
        
        for i, (title, desc, command) in enumerate(admin_menus):
            row = i // 2
            col = i % 2
            card = tk.Frame(menu_frame, bg='white', relief='flat', bd=1, cursor='hand2')
            card.grid(row=row, column=col, padx=15, pady=15, sticky='nsew')
            card.bind('<Button-1>', lambda e, cmd=command: cmd())
            menu_frame.grid_rowconfigure(row, weight=1)
            menu_frame.grid_columnconfigure(col, weight=1)
            tk.Label(card, text=title.split()[0], font=('Segoe UI', 36), bg='white').pack(pady=(20, 5))
            tk.Label(card, text=title, font=self.heading_font, bg='white', fg=self.colors['primary']).pack()
            tk.Label(card, text=desc, font=self.normal_font, bg='white', fg=self.colors['gray']).pack(pady=(5, 20))
    
    def show_reports(self):
        self.clear_window()
        self.create_header("Reports")
        
        main_frame = tk.Frame(self.root, bg=self.colors['light'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=15)
        
        self.cursor.execute("SELECT COUNT(*) FROM voters")
        total = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM voters WHERE voted=1")
        voted = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM voters WHERE face_encoding IS NOT NULL")
        face_count = self.cursor.fetchone()[0]
        
        report_frame = tk.Frame(main_frame, bg='white', relief='flat', bd=1)
        report_frame.pack(fill='both', expand=True)
        
        summary_frame = tk.Frame(report_frame, bg='white')
        summary_frame.pack(fill='x', padx=20, pady=15)
        
        reports = [
            ("Total Voters", total, self.colors['secondary']),
            ("Voted", voted, self.colors['success']),
            ("Remaining", total - voted, self.colors['warning']),
            ("Turnout %", f"{(voted/total*100):.1f}%" if total > 0 else "0%", self.colors['secondary']),
            ("Face Enrolled", face_count, self.colors['secondary'])
        ]
        
        for i, (label, value, color) in enumerate(reports):
            card = tk.Frame(summary_frame, bg=self.colors['light'], relief='flat', bd=1)
            card.grid(row=0, column=i, padx=8, pady=8, sticky='nsew')
            summary_frame.grid_columnconfigure(i, weight=1)
            tk.Label(card, text=str(value), font=('Segoe UI', 22, 'bold'), 
                    bg=self.colors['light'], fg=color).pack(pady=8)
            tk.Label(card, text=label, font=self.normal_font, 
                    bg=self.colors['light'], fg=self.colors['gray']).pack(pady=(0, 8))
    
    def show_voter_list(self):
        self.clear_window()
        self.create_header("Voter List")
        
        main_frame = tk.Frame(self.root, bg=self.colors['light'])
        main_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True)
        
        scrollbar_y = tk.Scrollbar(tree_frame, orient='vertical')
        scrollbar_x = tk.Scrollbar(tree_frame, orient='horizontal')
        
        columns = ('Voter ID', 'Name', 'Aadhaar', 'Face', 'Status')
        self.voter_tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                        yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.config(command=self.voter_tree.yview)
        scrollbar_x.config(command=self.voter_tree.xview)
        
        for i, col in enumerate(columns):
            self.voter_tree.heading(col, text=col)
            self.voter_tree.column(col, width=130)
        
        self.voter_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.cursor.execute("SELECT voter_id, name, aadhaar_id, face_encoding, voted FROM voters ORDER BY registered_date DESC")
        for row in self.cursor.fetchall():
            face_status = "✅" if row[3] else "❌"
            voted_status = "✅ Voted" if row[4] else "⏳ Not Voted"
            self.voter_tree.insert('', 'end', values=(row[0], row[1], f"XXXX-XXXX-{row[2][-4:]}", 
                                                       face_status, voted_status))
        
        tk.Button(main_frame, text="Export to CSV", command=self.export_to_csv,
                 font=self.button_font, bg=self.colors['secondary'], fg='white',
                 relief='flat', padx=20, pady=8, cursor='hand2').pack(pady=10)
    
    def export_to_csv(self):
        import csv
        filename = f"voter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.cursor.execute("SELECT voter_id, name, aadhaar_id, father_name, age, gender, phone_number, constituency_name, voted FROM voters")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Voter ID', 'Name', 'Aadhaar', "Father's Name", 'Age', 'Gender', 'Phone', 'Constituency', 'Voted'])
            writer.writerows(self.cursor.fetchall())
        
        messagebox.showinfo("Export Successful", f"Data exported to {filename}")
    
    def go_back(self):
        if self.current_role == 'admin':
            self.show_admin_dashboard()
        elif self.current_role == 'registrar':
            self.show_registration_form()
        elif self.current_role == 'verifier':
            self.show_verifier_dashboard()

# Run the application
if __name__ == "__main__":
    print("=" * 60)
    print("ELECTION COMMISSION - COMPLETE SYSTEM")
    print("=" * 60)
    print("Features:")
    print("  👑 Admin: Full access, reports, voter list")
    print("  📝 Registrar: Register voters with face capture")
    print("  🔍 Verifier: 2-Step verification (Aadhaar → Face)")
    print("  🔒 Strict Face Matching (50% threshold)")
    print("=" * 60)
    print("Login Credentials:")
    print("  👑 Admin     : admin / admin123")
    print("  📝 Registrar : registrar / registrar123")
    print("  🔍 Verifier  : verifier / verifier123")
    print("=" * 60)
    
    app = ElectionCommissionSystem()
