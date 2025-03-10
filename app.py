from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',           # Replace with your MySQL username
    'password': 'root',       # Replace with your MySQL password
    'database': 'healthcare'  # Database name
}

# Function to get database connection
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Patient Registration
@app.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO patients (name, email, password) VALUES (%s, %s, %s)',
                           (name, email, password))
            conn.commit()
            flash('Patient registered successfully!', 'success')
        except mysql.connector.IntegrityError:
            flash('Email already exists. Please use a different email.', 'error')
        except mysql.connector.Error as err:
            flash(f'An error occurred: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('home'))
    return render_template('register_patient.html')

# Doctor Registration
@app.route('/register/doctor', methods=['GET', 'POST'])
def register_doctor():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        specialization = request.form['specialization']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO doctors (name, email, password, specialization) VALUES (%s, %s, %s, %s)',
                           (name, email, password, specialization))
            conn.commit()
            flash('Doctor registered successfully!', 'success')
        except mysql.connector.IntegrityError:
            flash('Email already exists. Please use a different email.', 'error')
        except mysql.connector.Error as err:
            flash(f'An error occurred: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('home'))
    return render_template('register_doctor.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if user_type == 'patient':
            cursor.execute('SELECT * FROM patients WHERE email = %s AND password = %s',
                           (email, password))
        else:
            cursor.execute('SELECT * FROM doctors WHERE email = %s AND password = %s',
                           (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_type'] = user_type
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_type = session['user_type']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if user_type == 'patient':
        cursor.execute('SELECT * FROM appointments WHERE patient_id = %s',
                       (session['user_id'],))
    else:
        cursor.execute('SELECT * FROM appointments WHERE doctor_id = %s',
                       (session['user_id'],))
    appointments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', appointments=appointments, user_type=user_type)

# Schedule Appointment
@app.route('/schedule', methods=['GET', 'POST'])
def schedule_appointment():
    if 'user_id' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time = request.form['time']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Insert the appointment with is_approved set to NULL (pending approval)
            cursor.execute('''
                INSERT INTO appointments (patient_id, doctor_id, date, time, status, is_approved)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], doctor_id, date, time, 'Pending', None))
            conn.commit()
            flash('Appointment requested successfully! Waiting for doctor approval.', 'success')
        except mysql.connector.Error as err:
            flash(f'An error occurred: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('schedule.html', doctors=doctors)

# Cancel Appointment
@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        flash('You must be logged in to cancel an appointment.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete the appointment
        cursor.execute('DELETE FROM appointments WHERE id = %s', (appointment_id,))
        conn.commit()
        flash('Appointment canceled successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'An error occurred: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('dashboard'))
@app.route('/approve_appointment/<int:appointment_id>', methods=['POST'])
def approve_appointment(appointment_id):
    if 'user_id' not in session or session['user_type'] != 'doctor':
        flash('You must be logged in as a doctor to approve appointments.', 'error')
        return redirect(url_for('login'))

    # Get the action (approve or reject) from the form
    action = request.form['action']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if action == 'approve':
            # Approve the appointment
            cursor.execute('''
                UPDATE appointments
                SET is_approved = TRUE, status = 'Scheduled'
                WHERE id = %s AND doctor_id = %s
            ''', (appointment_id, session['user_id']))
            flash('Appointment approved successfully!', 'success')
        elif action == 'reject':
            # Reject the appointment
            cursor.execute('''
                UPDATE appointments
                SET is_approved = FALSE, status = 'Rejected'
                WHERE id = %s AND doctor_id = %s
            ''', (appointment_id, session['user_id']))
            flash('Appointment rejected.', 'success')
        conn.commit()
    except mysql.connector.Error as err:
        flash(f'An error occurred: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('dashboard'))
@app.route('/update_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def update_appointment(appointment_id):
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to update an appointment.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Get the updated data from the form
        new_date = request.form['date']
        new_time = request.form['time']
        new_status = request.form['status']

        try:
            # Update the appointment in the database
            cursor.execute('''
                UPDATE appointments
                SET date = %s, time = %s, status = %s
                WHERE id = %s
            ''', (new_date, new_time, new_status, appointment_id))
            conn.commit()
            flash('Appointment updated successfully!', 'success')
        except mysql.connector.Error as err:
            flash(f'An error occurred: {err}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard'))

    # Fetch the current appointment data for the form
    cursor.execute('SELECT * FROM appointments WHERE id = %s', (appointment_id,))
    appointment = cursor.fetchone()
    cursor.close()
    conn.close()

    if not appointment:
        flash('Appointment not found.', 'error')
        return redirect(url_for('dashboard'))

    return render_template('update_appointment.html', appointment=appointment)

# Update Profile
@app.route('/update_profile/<user_type>/<int:user_id>', methods=['GET', 'POST'])
def update_profile(user_type, user_id):
    # Check if the user is logged in and matches the user_id
    if 'user_id' not in session or session['user_id'] != user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Update the profile based on user type
        if user_type == 'doctor':
            specialization = request.form['specialization']
            cursor.execute('''
                UPDATE doctors 
                SET name = %s, email = %s, password = %s, specialization = %s 
                WHERE id = %s
            ''', (name, email, password, specialization, user_id))
        else:
            cursor.execute('''
                UPDATE patients 
                SET name = %s, email = %s, password = %s 
                WHERE id = %s
            ''', (name, email, password, user_id))

        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    # Fetch the current user's data
    if user_type == 'doctor':
        cursor.execute('SELECT * FROM doctors WHERE id = %s', (user_id,))
    else:
        cursor.execute('SELECT * FROM patients WHERE id = %s', (user_id,))

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))

    # Render the update profile template
    return render_template('update_profile.html', user=user, user_type=user_type)

# Delete Profile
@app.route('/delete/<user_type>/<int:user_id>')
def delete_profile(user_type, user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    if user_type == 'doctor':
        cursor.execute('DELETE FROM doctors WHERE id = %s', (user_id,))
    else:
        cursor.execute('DELETE FROM patients WHERE id = %s', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    session.clear()
    flash('Profile deleted successfully!', 'success')
    return redirect(url_for('home'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)