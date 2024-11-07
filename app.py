from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import re
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import urllib.parse as up

import pymysql
from flask_migrate import Migrate


pymysql.install_as_MySQLdb()

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Secret key and email credentials should be environment variables (for security)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret_key')  # Add default for development
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'your-email@gmail.com'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'your-email-password')
)

# Get the JawsDB URL from the environment variable
url = os.environ.get('JAWSDB_URL')

if url:
    # Parse the URL
    result = up.urlparse(url)

    # Configure the database connection using JawsDB credentials
    db_user = result.username
    db_password = result.password
    db_host = result.hostname
    db_name = result.path[1:]

    # Update SQLAlchemy database URI for Heroku JawsDB
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
else:
    # Fallback to the local database URI if not found
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/ehr_system'

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Doctor model (to replace the MySQL table)
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create the MySQL database tables (if they don't exist)
with app.app_context():
    db.create_all()

# Patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Demographics and basic information
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    
    # Medical history and conditions
    medical_history = db.Column(db.Text, nullable=True)
    medication = db.Column(db.String(200), nullable=True)
    allergies = db.Column(db.String(200), nullable=True)
    immunization_status = db.Column(db.String(200), nullable=True)
    
    # Other health records
    lab_results = db.Column(db.Text, nullable=True)
    radiology_images = db.Column(db.String(100), nullable=True)
    vital_signs = db.Column(db.String(200), nullable=True)
    
    # Additional fields for this project
    billing_info = db.Column(db.String(100), nullable=True)
    last_visit_date = db.Column(db.Date, nullable=True)

    doctor = db.relationship('Doctor', backref=db.backref('patients', lazy=True))

with app.app_context():
    db.create_all()  # Create tables in the database if they don't exist

# Configure the upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Add patient route
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'loggedin' in session:
        if request.method == 'POST':
            name = request.form.get('name')
            age = request.form.get('age')
            weight = request.form.get('weight')
            gender = request.form.get('gender')
            medical_history = request.form.get('medical_history')
            medication = request.form.get('medication')
            allergies = request.form.get('allergies')
            immunization_status = request.form.get('immunization_status')
            lab_results = request.form.get('lab_results')
            vital_signs = request.form.get('vital_signs')

            # File upload handling
            radiology_image_filename = None
            if 'radiology_images' in request.files:
                file = request.files['radiology_images']
                if file:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    radiology_image_filename = filename  # Save filename in the DB

            # Create a new Patient object and add it to the database
            new_patient = Patient(
                doctor_id=session['doctor_id'],
                name=name,
                age=age,
                weight=weight,
                gender=gender,
                medical_history=medical_history,
                medication=medication,
                allergies=allergies,
                immunization_status=immunization_status,
                lab_results=lab_results,
                radiology_images=radiology_image_filename,  # Store the image filename
                vital_signs=vital_signs
            )
            db.session.add(new_patient)
            db.session.commit()

            flash('Patient added successfully!', 'success')
            return redirect(url_for('view_patients'))  # Redirect to the view patients page

        return render_template('add_patient.html')
    else:
        flash('Please log in to add patients.', 'danger')
        return redirect(url_for('login'))

# View patients route
@app.route('/patients')
def view_patients():
    if 'loggedin' in session:
        # Fetch patients for the logged-in doctor
        patients = Patient.query.filter_by(doctor_id=session['doctor_id']).all()
        return render_template('view_patients.html', patients=patients)
    else:
        flash('Please log in to view patients.', 'danger')
        return redirect(url_for('login'))

# Edit patient route
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
        return redirect(url_for('view_patients'))

    return render_template('edit_patient.html', patient=patient)


# Delete patient route
@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient record deleted!', 'success')
    return redirect(url_for('view_patients'))


if __name__ == '__main__':
    app.run(debug=True)
