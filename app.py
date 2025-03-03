# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime
import json
import secrets
import random
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def add_image_column():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    # Check if the "image" column already exists
    c.execute("PRAGMA table_info(riddles);")
    columns = [column[1] for column in c.fetchall()]
    
    if "image" not in columns:
        c.execute("ALTER TABLE riddles ADD COLUMN image TEXT;")  # Add missing column
        conn.commit()
        print("Added 'image' column to riddles table.")

    conn.close()

# Run this once to update the database schema
add_image_column()


# Database initialization
def init_db():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Riddles table
    # c.execute('''
    #     CREATE TABLE IF NOT EXISTS riddles (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         question TEXT NOT NULL,
    #         answer TEXT NOT NULL,
    #         hint1 TEXT NOT NULL,
    #         hint2 TEXT NOT NULL,
    #         hint3 TEXT NOT NULL
    #     )
    # ''')


    # Modify riddles table to include an image field
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS riddles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            hint1 TEXT NOT NULL,
            hint2 TEXT NOT NULL,
            hint3 TEXT NOT NULL,
            image TEXT  -- New column for storing image filenames
        )
    ''')

    
    # User progress table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            riddle_id INTEGER NOT NULL,
            score INTEGER DEFAULT 10,
            completed INTEGER DEFAULT 0,
            hint1_used INTEGER DEFAULT 0,
            hint2_used INTEGER DEFAULT 0,
            hint3_used INTEGER DEFAULT 0,
            answer_attempt TEXT,
            completion_time TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (riddle_id) REFERENCES riddles (id),
            UNIQUE(user_id, riddle_id)
        )
    ''')
    
    # Insert admin user if not exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                  ('admin', 'admin@example.com', 'admin123', 1))
    
    # Insert sample riddles if none exist
    c.execute("SELECT COUNT(*) FROM riddles")
    if c.fetchone()[0] == 0:
        sample_riddles = [
            (
                "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?",
                "echo",
                "I repeat what I hear.",
                "You might find me in mountains and canyons.",
                "I am a returning sound."
            ),
            (
                "The more you take, the more you leave behind. What am I?",
                "footsteps",
                "I'm related to walking.",
                "I'm marks left behind.",
                "You make these when you walk on sand or snow."
            ),
            (
                "What has keys but no locks, space but no room, and you can enter but not go in?",
                "keyboard",
                "I'm used for typing.",
                "I have many buttons.",
                "You use me with a computer."
            ),
            (
                "What is always in front of you but can't be seen?",
                "future",
                "It's related to time.",
                "It hasn't happened yet.",
                "It's what's coming next in your life."
            ),
            (
                "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?",
                "map",
                "I represent real places.",
                "I'm used for navigation.",
                "I show you where things are located."
            )
        ]
        
        c.executemany("INSERT INTO riddles (question, answer, hint1, hint2, hint3) VALUES (?, ?, ?, ?, ?)", sample_riddles)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('riddle_test.db')
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                     (username, email, password))
            
            # Get the user id
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_id = c.fetchone()[0]
            
            # Initialize user progress for all riddles
            c.execute("SELECT id FROM riddles")
            riddle_ids = c.fetchall()
            
            for riddle_id in riddle_ids:
                c.execute("INSERT INTO user_progress (user_id, riddle_id) VALUES (?, ?)",
                         (user_id, riddle_id[0]))
                
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different one.')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('riddle_test.db')
        c = conn.cursor()
        
        c.execute("SELECT id, username, is_admin FROM users WHERE username = ? AND password = ?",
                 (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[2]
            
            if user[2]:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('test'))
        else:
            flash('Invalid username or password.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Also modify the test route to check if the user has been flagged for cheating
@app.route('/test')
def test():
    # This will now be the redirect to the first page (without images)
    return redirect(url_for('test_without_images'))

@app.route('/test_without_images') 
def test_without_images(): 
    if 'user_id' not in session: 
        flash('Please log in to take the test.') 
        return redirect(url_for('login')) 
     
    conn = sqlite3.connect('riddle_test.db') 
    c = conn.cursor() 
     
    # Check if the user has been flagged for cheating 
    c.execute(''' 
        SELECT COUNT(*)  
        FROM user_progress  
        WHERE user_id = ? AND answer_attempt = "FLAGGED-TAB-SWITCHING" 
    ''', (session['user_id'],)) 
     
    flag_count = c.fetchone()[0] 
     
    # If flagged, redirect to results 
    if flag_count > 0: 
        conn.close() 
        flash('You have been flagged for tab switching. Test access is restricted.') 
        return redirect(url_for('results')) 
     
    # Get all riddles WITHOUT images with user progress 
    c.execute(''' 
        SELECT r.id, r.question, r.image, up.score, up.completed, up.hint1_used, up.hint2_used, up.hint3_used 
        FROM riddles r 
        LEFT JOIN user_progress up ON r.id = up.riddle_id AND up.user_id = ? 
        WHERE r.image IS NULL OR r.image = ""
        ORDER BY r.id 
    ''', (session['user_id'],)) 
     
    riddle_data = c.fetchall() 
    conn.close() 
     
    riddles_without_images = [] 
    for riddle in riddle_data: 
        riddles_without_images.append({ 
            'id': riddle[0], 
            'question': riddle[1], 
            'image': riddle[2], 
            'score': riddle[3], 
            'completed': riddle[4], 
            'hint1_used': riddle[5], 
            'hint2_used': riddle[6], 
            'hint3_used': riddle[7], 
        }) 
     
    return render_template('test.html', riddles_without_images=riddles_without_images)

@app.route('/test_with_images') 
def test_with_images(): 
    if 'user_id' not in session: 
        flash('Please log in to take the test.') 
        return redirect(url_for('login')) 
     
    conn = sqlite3.connect('riddle_test.db') 
    c = conn.cursor() 
     
    # Check if the user has been flagged for cheating 
    c.execute(''' 
        SELECT COUNT(*)  
        FROM user_progress  
        WHERE user_id = ? AND answer_attempt = "FLAGGED-TAB-SWITCHING" 
    ''', (session['user_id'],)) 
     
    flag_count = c.fetchone()[0] 
     
    # If flagged, redirect to results 
    if flag_count > 0: 
        conn.close() 
        flash('You have been flagged for tab switching. Test access is restricted.') 
        return redirect(url_for('results')) 
     
    # Get all riddles WITH images with user progress 
    c.execute(''' 
        SELECT r.id, r.question, r.image, up.score, up.completed, up.hint1_used, up.hint2_used, up.hint3_used 
        FROM riddles r 
        LEFT JOIN user_progress up ON r.id = up.riddle_id AND up.user_id = ? 
        WHERE r.image IS NOT NULL AND r.image != ""
        ORDER BY r.id 
    ''', (session['user_id'],)) 
     
    riddle_data = c.fetchall() 
    conn.close() 
     
    riddles_with_images = [] 
    for riddle in riddle_data: 
        riddles_with_images.append({ 
            'id': riddle[0], 
            'question': riddle[1], 
            'image': riddle[2], 
            'score': riddle[3], 
            'completed': riddle[4], 
            'hint1_used': riddle[5], 
            'hint2_used': riddle[6], 
            'hint3_used': riddle[7], 
        }) 
     
    return render_template('test_images.html', riddles_with_images=riddles_with_images)

@app.route('/get_hint/<int:riddle_id>/<int:hint_num>', methods=['POST'])
def get_hint(riddle_id, hint_num):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Check if already completed
    c.execute("SELECT completed FROM user_progress WHERE user_id = ? AND riddle_id = ?",
             (session['user_id'], riddle_id))
    if c.fetchone()[0]:
        conn.close()
        return jsonify({'error': 'Riddle already completed'}), 400
    
    # Get hint
    hint_column = f"hint{hint_num}"
    c.execute(f"SELECT {hint_column} FROM riddles WHERE id = ?", (riddle_id,))
    hint = c.fetchone()[0]
    
    # Calculate score reduction
    score_reduction = 0
    if hint_num == 1:
        score_reduction = 2
        c.execute("UPDATE user_progress SET hint1_used = 1, score = score - ? WHERE user_id = ? AND riddle_id = ?",
                 (score_reduction, session['user_id'], riddle_id))
    elif hint_num == 2:
        score_reduction = 3
        c.execute("UPDATE user_progress SET hint2_used = 1, score = score - ? WHERE user_id = ? AND riddle_id = ?",
                 (score_reduction, session['user_id'], riddle_id))
    elif hint_num == 3:
        score_reduction = 4
        c.execute("UPDATE user_progress SET hint3_used = 1, score = score - ? WHERE user_id = ? AND riddle_id = ?",
                 (score_reduction, session['user_id'], riddle_id))
    
    conn.commit()
    
    # Get updated score
    c.execute("SELECT score FROM user_progress WHERE user_id = ? AND riddle_id = ?",
             (session['user_id'], riddle_id))
    updated_score = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'hint': hint,
        'score_reduction': score_reduction,
        'updated_score': updated_score
    })

@app.route('/submit_answer/<int:riddle_id>', methods=['POST'])
def submit_answer(riddle_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    answer = request.json.get('answer', '').strip().lower()
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Check if already completed
    c.execute("SELECT completed FROM user_progress WHERE user_id = ? AND riddle_id = ?",
             (session['user_id'], riddle_id))
    if c.fetchone()[0]:
        conn.close()
        return jsonify({'error': 'Riddle already completed'}), 400
    
    # Get correct answer
    c.execute("SELECT answer FROM riddles WHERE id = ?", (riddle_id,))
    correct_answer = c.fetchone()[0].lower()
    
    # Check answer
    is_correct = answer == correct_answer
    
    # Update user progress
    if is_correct:
        c.execute('''
            UPDATE user_progress 
            SET completed = 1, 
                answer_attempt = ?, 
                completion_time = ? 
            WHERE user_id = ? AND riddle_id = ?
        ''', (answer, datetime.now().isoformat(), session['user_id'], riddle_id))
        
        # Get current score
        c.execute("SELECT score FROM user_progress WHERE user_id = ? AND riddle_id = ?",
                 (session['user_id'], riddle_id))
        score = c.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'correct': True,
            'score': score
        })
    else:
        c.execute("UPDATE user_progress SET answer_attempt = ? WHERE user_id = ? AND riddle_id = ?",
                 (answer, session['user_id'], riddle_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'correct': False
        })

@app.route('/results')
def results():
    if 'user_id' not in session:
        flash('Please log in to view results.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get user's results
    c.execute('''
        SELECT r.id, r.question, r.answer, up.score, up.completed, 
               up.hint1_used, up.hint2_used, up.hint3_used, up.answer_attempt, up.completion_time
        FROM riddles r
        JOIN user_progress up ON r.id = up.riddle_id
        WHERE up.user_id = ?
        ORDER BY r.id
    ''', (session['user_id'],))
    
    results_data = c.fetchall()
    
    # Calculate total score
    c.execute('''
        SELECT SUM(score)
        FROM user_progress
        WHERE user_id = ? AND completed = 1
    ''', (session['user_id'],))
    
    total_score = c.fetchone()[0] or 0
    
    # Get total possible score
    c.execute("SELECT COUNT(*) * 10 FROM riddles")
    max_possible = c.fetchone()[0]
    
    # Calculate percentage score for progress bar
    percentage_score = int((total_score / max_possible) * 100) if max_possible > 0 else 0
    
    # Check if any riddles were flagged for cheating
    any_flagged = False
    for result in results_data:
        if result[8] == "FLAGGED-TAB-SWITCHING":
            any_flagged = True
            break
    
    conn.close()
    
    results = []
    for result in results_data:
        results.append({
            'id': result[0],
            'question': result[1],
            'correct_answer': result[2],
            'score': result[3],
            'completed': result[4],
            'hint1_used': result[5],
            'hint2_used': result[6],
            'hint3_used': result[7],
            'answer_attempt': result[8],
            'completion_time': result[9]
        })
    
    return render_template('results.html', 
                           results=results, 
                           total_score=total_score, 
                           max_possible=max_possible,
                           percentage_score=percentage_score,)
                        #    any_flagged=any_flagged)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get all users except admin
    c.execute('''
        SELECT u.id, u.username, u.email, 
               (SELECT COUNT(*) FROM user_progress WHERE user_id = u.id AND completed = 1) as completed_riddles,
               (SELECT SUM(score) FROM user_progress WHERE user_id = u.id AND completed = 1) as total_score
        FROM users u
        WHERE u.is_admin = 0
        ORDER BY total_score DESC
    ''')
    
    users_data = c.fetchall()
    
    # Get all riddles
    c.execute("SELECT id, question, answer FROM riddles ORDER BY id")
    riddles_data = c.fetchall()
    
    conn.close()
    
    users = []
    for user in users_data:
        users.append({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'completed_riddles': user[3],
            'total_score': user[4] or 0
        })
    
    riddles = []
    for riddle in riddles_data:
        riddles.append({
            'id': riddle[0],
            'question': riddle[1],
            'answer': riddle[2]
        })
    
    return render_template('admin_dashboard.html', users=users, riddles=riddles)

@app.route('/admin/add_riddle', methods=['POST'])
def add_riddle():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    question = request.form.get('question')
    answer = request.form.get('answer')
    hint1 = request.form.get('hint1')
    hint2 = request.form.get('hint2')
    hint3 = request.form.get('hint3')
    image = request.files.get('image')  # Get image from request

    if not all([question, answer, hint1, hint2, hint3]):
        return jsonify({'error': 'All fields are required'}), 400

    image_filename = None
    if image:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    try:
        # Add new riddle with image support
        c.execute('''
            INSERT INTO riddles (question, answer, hint1, hint2, hint3, image)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (question, answer, hint1, hint2, hint3, image_filename))
        
        riddle_id = c.lastrowid

        # Initialize progress for all users
        c.execute("SELECT id FROM users WHERE is_admin = 0")
        user_ids = c.fetchall()

        for user_id in user_ids:
            c.execute("INSERT INTO user_progress (user_id, riddle_id) VALUES (?, ?)",
                     (user_id[0], riddle_id))
        
        conn.commit()

        return jsonify({
            'success': True,
            'riddle_id': riddle_id,
            'image_url': f"/static/uploads/{image_filename}" if image_filename else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()




@app.route('/admin/delete_riddle/<int:riddle_id>', methods=['POST'])
def delete_riddle(riddle_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    try:
        # Delete user progress for this riddle
        c.execute("DELETE FROM user_progress WHERE riddle_id = ?", (riddle_id,))
        
        # Delete the riddle
        c.execute("DELETE FROM riddles WHERE id = ?", (riddle_id,))
        
        conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/user_detail/<int:user_id>')
def user_detail(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get user info
    c.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
    user_info = c.fetchone()
    
    if not user_info:
        conn.close()
        flash('User not found.')
        return redirect(url_for('admin_dashboard'))
    
    # Get user's results
    c.execute('''
        SELECT r.id, r.question, r.answer, up.score, up.completed, 
               up.hint1_used, up.hint2_used, up.hint3_used, up.answer_attempt, up.completion_time
        FROM riddles r
        JOIN user_progress up ON r.id = up.riddle_id
        WHERE up.user_id = ?
        ORDER BY r.id
    ''', (user_id,))
    
    results_data = c.fetchall()
    
    # Calculate total score
    c.execute('''
        SELECT SUM(score)
        FROM user_progress
        WHERE user_id = ? AND completed = 1
    ''', (user_id,))
    
    total_score = c.fetchone()[0] or 0
    
    # Get total possible score
    c.execute("SELECT COUNT(*) * 10 FROM riddles")
    max_possible = c.fetchone()[0]
    
    # Calculate percentage score for progress bar
    percentage_score = int((total_score / max_possible * 100)) if max_possible > 0 else 0
    
    conn.close()
    
    user = {
        'id': user_id,
        'username': user_info[0],
        'email': user_info[1]
    }
    
    results = []
    for result in results_data:
        results.append({
            'id': result[0],
            'question': result[1],
            'correct_answer': result[2],
            'score': result[3],
            'completed': result[4],
            'hint1_used': result[5],
            'hint2_used': result[6],
            'hint3_used': result[7],
            'answer_attempt': result[8],
            'completion_time': result[9]
        })
    
    return render_template('user_detail.html', 
                           user=user,
                           results=results, 
                           total_score=total_score, 
                           max_possible=max_possible,
                           percentage_score=percentage_score)

# Add this endpoint to app.py
@app.route('/record_cheating_attempt', methods=['POST'])
def record_cheating_attempt():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    tab_switches = data.get('tab_switches', 0)
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # First, check if the user has any incomplete riddles
    c.execute('''
        SELECT COUNT(*) 
        FROM user_progress 
        WHERE user_id = ? AND completed = 0
    ''', (session['user_id'],))
    
    incomplete_count = c.fetchone()[0]
    
    if incomplete_count > 0:
        # Add cheating flag to all incomplete riddles
        # This will prevent further attempts on these riddles
        c.execute('''
            UPDATE user_progress 
            SET completed = 1, 
                score = 0,
                completion_time = ?,
                answer_attempt = "FLAGGED-TAB-SWITCHING"
            WHERE user_id = ? AND completed = 0
        ''', (datetime.now().isoformat(), session['user_id']))
        
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})



@app.route('/admin/export_results')
def export_results():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get all user results
    c.execute('''
        SELECT 
            u.id as user_id, 
            u.username, 
            u.email,
            r.id as riddle_id,
            r.question,
            r.answer as correct_answer,
            up.score,
            up.completed,
            up.hint1_used,
            up.hint2_used,
            up.hint3_used,
            up.answer_attempt,
            up.completion_time
        FROM users u
        JOIN user_progress up ON u.id = up.user_id
        JOIN riddles r ON up.riddle_id = r.id
        WHERE u.is_admin = 0
        ORDER BY u.id, r.id
    ''')
    
    columns = [desc[0] for desc in c.description]
    results = c.fetchall()
    
    conn.close()
    
    # Convert to list of dicts for JSON
    results_list = []
    for row in results:
        result_dict = {}
        for i, col in enumerate(columns):
            result_dict[col] = row[i]
        results_list.append(result_dict)
    
    return jsonify(results_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename=f'uploads/{filename}'))

if __name__ == '__main__':
    app.run(debug=True)