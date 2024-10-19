from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymysql import MySQL
from flask_bcrypt import Bcrypt
import pymysql
import re

# Use PyMySQL as MySQLdb replacement
pymysql.install_as_MySQLdb()


app = Flask(__name__)
bcrypt = Bcrypt(app)

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Default user for XAMPP MySQL
app.config['MYSQL_PASSWORD'] = ''  # Leave blank as XAMPP root user has no password by default
app.config['MYSQL_DB'] = 'ehr_system'  # Name of your database


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
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM doctors WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account and bcrypt.check_password_hash(account['password'], password):
            session['loggedin'] = True
            session['doctor_id'] = account['doctor_id']
            session['username'] = account['username']
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect username or password', 'danger')
    return render_template('login.html')

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Password hashing
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Ensure form data is valid
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM doctors WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            flash('Account already exists', 'danger')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!', 'danger')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers', 'danger')
        else:
            cursor.execute('INSERT INTO doctors (username, password, email) VALUES (%s, %s, %s)', (username, hashed_password, email))
            mysql.connection.commit()
            flash('You have successfully registered!', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

# Route for doctor dashboard after login
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        return f"Welcome {session['username']}! This is your dashboard."
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
