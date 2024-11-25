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
'''app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret_key')  # Add default for development
app.config.update(
    MAIL_SERVER='smtp.mail.yahoo.com',
    MAIL_PORT=465,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'oscarkyamuweno@yahoo.com'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'Godjesus44me.')
) '''


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
    confirmed = db.Column(db.Boolean, default=False)

# Creates the MySQL database tables (if they don't exist)
with app.app_context():
    db.create_all()

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        doctor = Doctor.query.filter_by(username=username).first()

        if doctor:
            #if not doctor.confirmed:
                #message = "Please confirm your email before logging in."
            if bcrypt.check_password_hash(doctor.password, password):
                session['loggedin'] = True
                session['doctor_id'] = doctor.id
                session['username'] = doctor.username
                return redirect(url_for('dashboard'))
            else:
                message = "Incorrect password. Please try again."
        else:
            message = "No account found with this username. Please register first."

    return render_template('login.html', message=message)



# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.mail.yahoo.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'oscarkyamuwendo@yahoo.com'
app.config['MAIL_PASSWORD'] = 'vdvifzmtxjyigmse'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)


# Set up token serializer
def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
    except:
        return False
    return email



# Forgot password configuration
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = Doctor.query.filter_by(email=email).first()  # Check if user exists

        if user:
            # Generate a secure token for password reset
            token = generate_password_reset_token(user.id)
            reset_url = url_for('reset_password', token=token, _external=True)

            # Send reset email
            msg = Message("Password Reset Request",
                          sender= ("Elehere Support","oscarkyamuwendo@yahoo.com"),
                          recipients=[email])
            msg.body = f"To reset your password, visit the following link: {reset_url}"
            mail.send(msg)
            
            flash("A password reset link has been sent to your email.", "success")
            return redirect(url_for('login'))
        else:
            flash("Email not found. Please check and try again.", "danger")
            return redirect(url_for('forgot_password'))

                                        # Render the forgot_password form on a GET request
    return render_template('forgot_password.html')


# Function to generate reset token
def generate_password_reset_token(user_id):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(user_id, salt='password-reset-salt')


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
                  sender= ("Elehere Support","oscarkyamuwendo@yahoo.com"),  # Replace with your sender email
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
        username = request.form['reg-username']
        password = request.form['reg-password']
        confirm_password = request.form['confirm-password']
        email = request.form['email']

        if password != confirm_password:
            return render_template(
                'register.html',
                title="Error",
                message="Passwords do not match! Please try again."
            )

        if Doctor.query.filter_by(username=username).first() or Doctor.query.filter_by(email=email).first():
            return render_template(
                'register.html',
                title="Error",
                message="Username or Email already exists! Please use another or log in."
            )

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_doctor = Doctor(username=username, email=email, password=hashed_password, confirmed=False)
        db.session.add(new_doctor)
        db.session.commit()

        # Generate confirmation token and send email
        token = serializer.dumps(email, salt='email-confirmation-salt')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = Message('Confirm Your Account', 
                      sender=("Elehere Support", "oscarkyamuwendo@yahoo.com"),
                      recipients=[email])
        msg.body = f"Click the link to confirm your account: {confirm_url}"
        mail.send(msg)

        # Return modal data
        return render_template(
            'register.html',
            title="Registration Successful",
            message="Registration successful! Please check your email for the activation link."
        )

    return render_template('register.html')



@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=3600)
    except:
        return render_template('activation_failed.html', message="The confirmation link is invalid or has expired.")

    doctor = Doctor.query.filter_by(email=email).first_or_404()
    if doctor.confirmed:
        return render_template('activation_success.html', message="Your account is already confirmed. Please log in.")
    
    doctor.confirmed = True
    db.session.commit()
    return render_template('activation_success.html', message="Your account has been activated! You may now log in.")



@app.route('/doctors')
def view_doctors():
    if 'loggedin' in session:  # Optional: Only allow logged-in users to view this page
        doctors = Doctor.query.all()  # Fetch all doctors from the database
        return render_template('doctors.html', doctors=doctors)
    else:
        return redirect(url_for('login'))


# Route for doctor dashboard after login
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'loggedin' in session:
        # Get search parameters from request args
        name_query = request.args.get('name')
        age_query = request.args.get('age')

        # Start with a query filtering by doctor_id
        query = Patient.query.filter_by(doctor_id=session['doctor_id'])

        # Apply filters based on search criteria
        if name_query:
            query = query.filter(Patient.name.ilike(f"%{name_query}%"))  # Case-insensitive search
        if age_query:
            query = query.filter(Patient.age == age_query)

        # Execute the query
        patients = query.all()
        
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
    return redirect(url_for('index'))

# patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Demographics and basic information
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # Add gender field
    
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
with app.app_context():
    db.create_all()  # Create tables in the database if they don't exist

# Configure the upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = 'static/uploads'


# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Add patient route
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'loggedin' in session:
        if request.method == 'POST':
            # Handle file upload for radiology image
            radiology_image = request.files.get('radiology_images')
            radiology_image_filename = None  # Default to None if no image is uploaded
            
            if radiology_image and radiology_image.filename != '':
                filename = secure_filename(radiology_image.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                radiology_image.save(upload_path)
                radiology_image_filename = filename  # Store the filename to save in the database
            
            # Patient data processing here
            new_patient = Patient(
                doctor_id=session['doctor_id'],
                name=request.form.get('name'),
                age=request.form.get('age'),
                weight=request.form.get('weight'),
                gender=request.form.get('gender'),
                medical_history=request.form.get('medical_history'),
                medication=request.form.get('medication'),
                allergies=request.form.getlist('allergies'),
                immunization_status=request.form.get('immunization_status'),
                lab_results=request.form.get('lab_results'),
                radiology_images=radiology_image_filename,  # Save filename of the uploaded image
                vital_signs=request.form.get('vital_signs'),
                billing_info=request.form.get('billing_info'),
                last_visit_date=request.form.get('last_visit_date')
            )
            db.session.add(new_patient)
            db.session.commit()

            # Render the success confirmation
            return render_template('add_patient.html', success=True)

        return render_template('add_patient.html', success=False)
    else:
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
    success = False  # Flag for displaying acknowledgment

    if request.method == 'POST':
        try:
            # Update patient details from the form
            patient.name = request.form['name']
            patient.age = int(request.form['age'])
            patient.weight = float(request.form['weight'])
            patient.gender = request.form['gender']
            patient.medical_history = request.form['medical_history']
            patient.medication = request.form['medication']

            # Convert list of allergies to a comma-separated string
            patient.allergies = ', '.join(request.form.getlist('allergies'))

            # Optional fields with defaults
            patient.immunization_status = request.form.get('immunization_status', 'Not Provided')
            patient.lab_results = request.form.get('lab_results', '')
            patient.billing_info = request.form.get('billing_info', '')

            # Validate and update last visit date
            patient.last_visit_date = request.form['last_visit_date'] if request.form['last_visit_date'] else None

            # Handle radiology image upload
            radiology_image = request.files.get('radiology_images')
            if radiology_image and radiology_image.filename != '':
                filename = secure_filename(radiology_image.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                radiology_image.save(upload_path)
                patient.radiology_images = filename  # Save filename in the database

            # Commit changes to the database
            db.session.commit()
            success = True
        except Exception as e:
            # Handle any errors gracefully
            db.session.rollback()
            error_message = f"An error occurred while updating the patient's information: {str(e)}"
            return render_template('edit_patient.html', patient=patient, success=False, error=error_message)

    return render_template('edit_patient.html', patient=patient, success=success)


# delete patient
@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient record deleted!', 'success')
    return redirect(url_for('view_patients'))

# about
@app.route('/about')
def about():

    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
