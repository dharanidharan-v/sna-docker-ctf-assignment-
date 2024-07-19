import subprocess
from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3
from threading import Lock

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create a directory to hide the flag
FLAG_FILE = 'flag.txt'
# Ensure flag.txt exists in the root directory
with open(FLAG_FILE, 'w') as f:
    f.write('FLAG{COMMAND_INJECTION_FLAG}')

# Initialize the database with sample data
def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                comment TEXT NOT NULL
            )
        ''')
        cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
        cursor.execute("INSERT INTO users (username, password) VALUES ('user', 'password')")
        conn.commit()
        
        # Create table for tracking found flags
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS found_flags (
                flag TEXT PRIMARY KEY
            )
        ''')
        conn.commit()

# Initialize flag count and track found flags
flags_found = 0
flags_lock = Lock()

def increment_flags_found(flag):
    global flags_found
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM found_flags WHERE flag = ?", (flag,))
        if cursor.fetchone()[0] == 0:  # If flag is not found
            cursor.execute("INSERT INTO found_flags (flag) VALUES (?)", (flag,))
            conn.commit()
            flags_found += 1

@app.route('/')
def index():
    return render_template('index.html', flags_found=flags_found)

@app.route('/submit_flag/<challenge>', methods=['POST'])
def submit_flag(challenge):
    flag = request.form['flag']
    
    valid_flags = {
        'funny_database_queries': 'FLAG{SQL_INJECTION_FLAG}',
        'sneaky_scripts': 'FLAG{XSS_FLAG}',
        'dodgy_file_uploads': 'FLAG{FILE_UPLOAD_FLAG}',
        'commandos_attack': 'FLAG{COMMAND_INJECTION_FLAG}'
    }

    correct_flag = valid_flags.get(challenge)

    if flag == correct_flag:
        increment_flags_found(correct_flag)
        return redirect(url_for('index'))
    else:
        return "Incorrect flag. Please try again."

@app.route('/challenge/funny_database_queries', methods=['GET', 'POST'])
def funny_database_queries():
    hint = "Sometimes databases trust user input too much..."
    message = None
    flag = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                flag = "FLAG{SQL_INJECTION_FLAG}"
                message = "Login successful! Here's your flag: FLAG{SQL_INJECTION_FLAG}"
            else:
                message = "Login failed! Please try again."
            return render_template('challenge.html', challenge='funny_database_queries', hint=hint, form_type='login', message=message, flag=flag)
    return render_template('challenge.html', challenge='funny_database_queries', hint=hint, form_type='login')

@app.route('/challenge/sneaky_scripts', methods=['GET', 'POST'])
def sneaky_scripts():
    hint = "Be careful what you let others post on your site..."
    message = None
    flag = None
    comments = []
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email, comment FROM comments")
        comments = cursor.fetchall()
    
    if request.method == 'POST':
        email = request.form['email']
        comment = request.form['comment']

        if email and comment:
            with sqlite3.connect('database.db') as conn:
                conn.execute("INSERT INTO comments (email, comment) VALUES (?, ?)", (email, comment))
                conn.commit()

            if "<script>" in comment:
                flag = 'FLAG{XSS_FLAG}'
                message = "Comment posted and XSS detected! Here's your flag: FLAG{XSS_FLAG}"
            else:
                message = "Comment posted, but no XSS detected."
        else:
            message = "Please provide both email and comment."

    return render_template('challenge.html', challenge='sneaky_scripts', hint=hint, message=message, flag=flag, form_type='comment', comments=comments)

@app.route('/challenge/dodgy_file_uploads', methods=['GET', 'POST'])
def dodgy_file_uploads():
    hint = "Not all files are safe to upload..."
    feedback = ""
    flag = None
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            if file.filename == 'shell.php':
                flag = 'FLAG{FILE_UPLOAD_FLAG}'
                feedback = "Success! File upload vulnerability triggered. Here's your flag: FLAG{FILE_UPLOAD_FLAG}"
            else:
                feedback = "File uploaded."
    return render_template('challenge.html', challenge='dodgy_file_uploads', hint=hint, form_type='file_upload', feedback=feedback, flag=flag)

@app.route('/challenge/commandos_attack', methods=['GET', 'POST'])
def commandos_attack():
    hint = "Sometimes commands can do more than expected..."
    output = None
    flag = None
    
    if request.method == 'POST':
        command = request.form['command']
        
        # Check if the command is to execute
        if command:
            try:
                # Only allow ping commands, not specific commands
                if 'ping' in command.lower():
                    output = subprocess.getoutput(command)
                elif ';' in command:  # Check for command injection
                    # Execute the command and capture output
                    output = subprocess.getoutput(command)
                    
                    # Look for flag.txt file
                    if 'ls' in command.lower() and 'flag.txt' in output:
                        with open(FLAG_FILE, 'r') as f:
                            flag = f.read().strip()
            except Exception as e:
                output = f"Error: {str(e)}"

    return render_template('challenge.html', challenge='commandos_attack', hint=hint, form_type='command_injection', output=output, flag=flag)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
