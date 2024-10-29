from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import re
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

import pymysql
from flask_migrate import Migrate


pymysql.install_as_MySQLdb()

app = Flask(__name__)
bcrypt = Bcrypt(app)

# MySQL configuration (XAMPP MySQL connection)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/ehr_system'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Secret key for session management
app.secret_key = 'your_secret_key'

# Doctor model (to replace the MySQL table)
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create the MySQL database tables (if they don't exist)
with app.app_context():
    db.create_all()

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
        doctor = Doctor.query.filter_by(username=username).first()

        # Check if the doctor exists and the password matches
        if doctor and bcrypt.check_password_hash(doctor.password, password):
            # Set session details
            session['loggedin'] = True
            session['doctor_id'] = doctor.id
            session['username'] = doctor.username
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to the dashboard
        else:
            flash('Incorrect username or password', 'danger')
    
    return render_template('login.html')


# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-email-password'  # Replace with your email password or app-specific password
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

# Forgot password configuration
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        doctor = Doctor.query.filter_by(email=email).first()

        if doctor:
            # Generate a reset token (this can be done using itsdangerous or JWT)
            token = generate_reset_token(doctor.id)  # You will create this function
            send_reset_email(doctor.email, token)    # You will create this function

            flash('A password reset email has been sent.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email does not exist!', 'danger')
    
    return render_template('forgot_password.html')

# Function to generate reset token
def generate_reset_token(doctor_id):
    s = URLSafeTimedSerializer(app.secret_key)
    return s.dumps(doctor_id, salt='password-reset-salt')

# Function to verify the reset token
def verify_reset_token(token, expiration=3600):  # Expiration time is 1 hour (3600 seconds)
    s = URLSafeTimedSerializer(app.secret_key)
    try:
        doctor_id = s.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return None
    return doctor_id

# send reset email
def send_reset_email(email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message('Password Reset Request', 
                  sender='your-email@gmail.com',  # Replace with your sender email
                  recipients=[email])
    msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email and no changes will be made.
'''
    mail.send(msg)

# password reset route
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    doctor_id = verify_reset_token(token)
    if not doctor_id:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password', token=token))

        # Update password
        doctor = Doctor.query.get(doctor_id)
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        doctor.password = hashed_password
        db.session.commit()

        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')


# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Ensure all fields are present
        if 'reg-username' in request.form and 'reg-password' in request.form and 'email' in request.form:
            username = request.form['reg-username']
            password = request.form['reg-password']
            confirm_password = request.form['confirm-password']
            email = request.form['email']

            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match!', 'danger')
                return redirect(url_for('register'))

            # Check if the username or email already exists
            if Doctor.query.filter_by(username=username).first() or Doctor.query.filter_by(email=email).first():
                flash('Username or Email already exists!', 'danger')
                return redirect(url_for('register'))

            # Password hashing
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert into the database
            new_doctor = Doctor(username=username, email=email, password=hashed_password)
            db.session.add(new_doctor)
            db.session.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))  # Redirect to login page after registration
        else:
            flash('Please fill out all fields.', 'danger')
    
    return render_template('register.html')

@app.route('/doctors')
def view_doctors():
    if 'loggedin' in session:  # Optional: Only allow logged-in users to view this page
        doctors = Doctor.query.all()  # Fetch all doctors from the database
        return render_template('doctors.html', doctors=doctors)
    else:
        return redirect(url_for('login'))


# Route for doctor dashboard after login
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        # Fetch patients for the logged-in doctor
        patients = Patient.query.filter_by(doctor_id=session['doctor_id']).all()
        return render_template('dashboard.html', patients=patients)
    else:
        flash('Please log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))

# Logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('doctor_id', None)
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

# patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)  # Foreign key to Doctor

    # Demographics and basic information
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=True)
    
    # Medical history and conditions
    medical_history = db.Column(db.Text, nullable=True)
    medication = db.Column(db.String(200), nullable=True)
    allergies = db.Column(db.String(200), nullable=True)
    immunization_status = db.Column(db.String(200), nullable=True)

    # Other health records
    lab_results = db.Column(db.Text, nullable=True)
    radiology_images = db.Column(db.String(100), nullable=True)  # Could be a path to the image
    vital_signs = db.Column(db.String(200), nullable=True)

    # Additional fields for this project
    billing_info = db.Column(db.String(100), nullable=True)
    last_visit_date = db.Column(db.Date, nullable=True)  # Date of last visit

    doctor = db.relationship('Doctor', backref=db.backref('patients', lazy=True))

with app.app_context():
    db.create_all()  # Create tables in the database if they don't exist

# Add patient route
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'loggedin' in session:
        if request.method == 'POST':
            name = request.form['name']
            age = request.form['age']
            medical_history = request.form['medical_history']
            medication = request.form['medication']
            allergies = request.form['allergies']
            immunization_status = request.form['immunization_status']
            lab_results = request.form['lab_results']
            vital_signs = request.form['vital_signs']
            
            # Retrieve the radiology images file (or handle absence)
            radiology_images = request.files.get('radiology_images')
            if radiology_images:
                # You can handle file storage here, e.g., save to server
                # radiology_images.save(os.path.join('your/upload/directory', radiology_images.filename))
                # For now, just saving the filename to the database field
                radiology_images = radiology_images.filename

            # Create a new Patient object and add it to the database
            new_patient = Patient(
                doctor_id=session['doctor_id'],
                name=name,
                age=age,
                medical_history=medical_history,
                medication=medication,
                allergies=allergies,
                immunization_status=immunization_status,
                lab_results=lab_results,
                radiology_images=radiology_images,  # Save filename or path here
                vital_signs=vital_signs
            )
            db.session.add(new_patient)
            db.session.commit()

            flash('Patient added successfully!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('add_patient.html')
    else:
        flash('Please log in to add patients.', 'danger')
        return redirect(url_for('login'))

# view patient
@app.route('/patients')
def view_patients():
    if 'loggedin' in session:
        # Fetch patients for the logged-in doctor
        patients = Patient.query.filter_by(doctor_id=session['doctor_id']).all()
        return render_template('view_patients.html', patients=patients)
    else:
        flash('Please log in to view patients.', 'danger')
        return redirect(url_for('login'))

# edit_patient
@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        patient.name = request.form['name']
        patient.age = request.form['age']
        patient.medical_history = request.form['medical_history']
        patient.medication = request.form['medication']
        patient.allergies = request.form['allergies']
        patient.immunization_status = request.form['immunization_status']
        patient.lab_results = request.form['lab_results']
        patient.radiology_images = request.form['radiology_images']
        patient.vital_signs = request.form['vital_signs']

        db.session.commit()
        flash('Patient record updated!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_patient.html', patient=patient)


# delete patient
@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient record deleted!', 'success')
    return redirect(url_for('view_patients'))


if __name__ == '__main__':
    app.run(debug=True)
