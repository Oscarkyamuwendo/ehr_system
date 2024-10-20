from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymysql import MySQL
from flask_bcrypt import Bcrypt
import pymysql
import re

app = Flask(__name__)
bcrypt = Bcrypt(app)

# MySQL configuration
# MySQL configuration (Dictionary format)
app.config['MYSQL_DB_ARGS'] = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ehr_system'
}

# Initialize MySQL
mysql = MySQL(app)

# Secret key for session management
app.secret_key = 'your_secret_key'

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Fetch the doctor from the database
        print(f"mysql object exists: {mysql}")  # Add this line before cursor creation
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM doctors WHERE username = %s', (username,))
        doctor = cursor.fetchone()
        cursor.close()

        cursor = mysql.connection.cursor()  # Original line
# Add this line before the cursor creation
        print(f"mysql.connection exists: {bool(mysql.connection)}")
        
        # Check if the doctor exists and the password matches
        if doctor and bcrypt.check_password_hash(doctor['password'], password):
            # Set session details
            session['loggedin'] = True
            session['doctor_id'] = doctor['doctor_id']
            session['username'] = doctor['username']
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect username or password', 'danger')
    
    return render_template('login.html')

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Ensure all fields are present
        if 'reg-username' in request.form and 'reg-password' in request.form and 'email' in request.form:
            username = request.form['reg-username']  # Using 'reg-username' from the form
            password = request.form['reg-password']  # Using 'reg-password' from the form
            confirm_password = request.form['confirm-password']  # Using 'confirm-password' from the form
            email = request.form['email']

            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match!', 'danger')
                return redirect(url_for('register'))

            # Password hashing
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert into the database
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO doctors (username, email, password) VALUES (%s, %s, %s)', (username, email, hashed_password))
            mysql.connection.commit()
            cursor.close()

            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Please fill out all fields.', 'danger')
    
    return render_template('register.html')

# Route for doctor dashboard after login
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))

# Logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('doctor_id', None)
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
