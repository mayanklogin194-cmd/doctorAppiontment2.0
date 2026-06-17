from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import re

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_in_production'

# Upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ====================== IMPORTS ======================
import admin_management
import doctorappointment
from Appointment import get_specializations_for_web, get_doctors_for_web, get_valid_dates_for_doctor, get_available_slots_web, book_appointment_web
from Report_mode import extract_text_from_pdf, extract_medical_values, check_health_simple, generate_bar_chart, generate_pie_chart, generate_ring_charts
from Showappointment import get_patient_appointments
from user_login import create_new_user_web

# ====================== ROUTES ======================

@app.route('/')
def index():
    if 'admin' in session:
        return redirect(url_for('admin_dashboard'))
    elif 'doctor' in session:
        return redirect(url_for('doctor_dashboard'))
    elif 'customer' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ---------------- PATIENT LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin' in session: return redirect(url_for('admin_dashboard'))
    if 'doctor' in session: return redirect(url_for('doctor_dashboard'))
    if 'customer' in session: return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email'].strip()
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("❌ Invalid email format.", 'error')
            return render_template('login.html', active_panel='login')

        from pymongo import MongoClient
        uri = "mongodb+srv://MayankRathore:Mk01092004@cluster0.rawu8tm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        client = MongoClient(uri)
        db = client["Health_status_shower"]
        customer = db["Customer"].find_one({"email": email})

        if customer:
            session['customer'] = {
                'Patient_id': customer['Patient_id'],
                'Name': customer['Name'],
                'email': customer['email']
            }
            flash(f"✅ Welcome back, {customer['Name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("❌ No account found with that email.", 'error')
            return render_template('login.html', active_panel='register', email_prefill=email)

    return render_template('login.html', active_panel='login')

# ---------------- ADMIN ROUTES ----------------
@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        master_key = request.form['master_key']
        try:
            admin_management.register_admin(email, name, master_key)
            flash("✅ Admin registration successful!", "success")
            return redirect(url_for('admin_login'))
        except ValueError as e:
            flash(str(e), "error")
    return render_template('admin_register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        master_key = request.form['master_key']
        admin = admin_management.verify_admin_login(email, master_key)
        if admin:
            session['admin'] = {'email': admin['email'], 'name': admin['name']}
            flash(f"💻 Welcome Admin {admin['name']}!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("❌ Invalid credentials.", "error")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("🔓 Signed out successfully.", "success")
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session:
        flash("🔒 Admin access required.", "warning")
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        action = request.form.get('action')
        # Doctor & Patient actions (same as your original)
        if action == 'add_doctor':
            try:
                admin_management.add_new_doctor(
                    request.form['doc_name'], request.form['doc_email'],
                    request.form['specialization'], request.form['availability'],
                    request.form['doc_phone'], request.form.getlist('slots')
                )
                flash("🩺 Doctor onboarded successfully!", "success")
            except ValueError as e:
                flash(str(e), "error")
        # ... (add other actions: edit_doctor, delete_doctor, edit_patient, delete_patient)
        return redirect(url_for('admin_dashboard'))

    patients = admin_management.get_all_patients()
    doctors = admin_management.get_all_doctors()
    return render_template('admin_dashboard.html', admin=session['admin'], patients=patients, doctors=doctors)

# ---------------- DOCTOR LOGIN ----------------
@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        doctor_id = doctorappointment.existing_user(email)
        if doctor_id:
            session['doctor'] = {'doctor_id': doctor_id, 'email': email}
            flash("🩺 Doctor login successful!", 'success')
            return redirect(url_for('doctor_dashboard'))
        else:
            flash("❌ Doctor not found.", 'error')
    return render_template('doctor_login.html')

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'doctor' not in session:
        return redirect(url_for('doctor_login'))
    doctor_id = session['doctor']['doctor_id']
    today_data = doctorappointment.get_appointments(doctor_id, "1")
    upcoming_data = doctorappointment.get_appointments(doctor_id, "2")
    return render_template('doctor_dashboard.html',
                           email=session['doctor']['email'],
                           appointments_today=today_data.get('appointments', []),
                           appointments_upcoming=upcoming_data.get('appointments', []))

# ---------------- PATIENT ROUTES ----------------
@app.route('/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        try:
            new_data = create_new_user_web(
                request.form['name'], request.form['email'],
                request.form['contact_number'], request.form['gender'],
                int(request.form['age']), int(request.form['pincode'])
            )
            session['customer'] = {
                'Patient_id': new_data['Patient_id'],
                'Name': new_data['Name'],
                'email': new_data['email']
            }
            flash("✅ Registration successful!", 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"❌ Error: {e}", 'error')
    return render_template('login.html', active_panel='register')

@app.route('/dashboard')
def dashboard():
    if 'customer' not in session:
        return redirect(url_for('login'))
    patient_id = session['customer']['Patient_id']
    appointments = get_patient_appointments(patient_id)
    return render_template('dashboard.html', customer_name=session['customer']['Name'], appointments=appointments)

@app.route('/report_mode', methods=['GET', 'POST'])
def report_mode():
    if 'customer' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['report_file']
        if file and file.filename.endswith('.pdf'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            try:
                text = extract_text_from_pdf(filepath)
                values = extract_medical_values(text)
                status = check_health_simple(values)
                bar = generate_bar_chart(values, status)
                pie = generate_pie_chart(status)
                rings = generate_ring_charts(values, status)
                return render_template('report_results.html',
                                       extracted_values=values,
                                       status_dict=status,
                                       bar_chart=bar,
                                       pie_chart=pie,
                                       ring_charts=rings)
            except Exception as e:
                flash(f"Error: {e}", 'error')
        return redirect(request.url)
    return render_template('report_upload.html')

@app.route('/appointment_booking')
def appointment_booking():
    if 'customer' not in session:
        return redirect(url_for('login'))
    return render_template('appointment_booking.html')

# ---------------- APPOINTMENT APIs ----------------
@app.route('/api/specializations')
def api_specializations():
    return jsonify(get_specializations_for_web())

@app.route('/api/doctors')
def api_doctors():
    spec = request.args.get('spec')
    if not spec: return jsonify([])
    doctors = get_doctors_for_web(spec)
    return jsonify([{'doctor_id': d.get('doctor_id'), 'name': d.get('name'), 'specialization': d.get('specialization')} for d in doctors])

@app.route('/api/dates')
def api_dates():
    doctor_id = request.args.get('doctor_id')
    if not doctor_id: return jsonify([])
    for spec in get_specializations_for_web():
        for doc in get_doctors_for_web(spec):
            if str(doc.get('doctor_id')) == doctor_id:
                return jsonify(get_valid_dates_for_doctor(doc.get("availability", "")))
    return jsonify([])

@app.route('/api/slots')
def api_slots():
    doctor_id = request.args.get('doctor_id')
    date = request.args.get('date')
    if not doctor_id or not date: return jsonify([])
    return jsonify(get_available_slots_web(doctor_id, date))

@app.route('/confirm_appointment', methods=['POST'])
def confirm_appointment():
    if 'customer' not in session:
        return jsonify({"success": False, "error": "Not logged in"})
    data = request.get_json()
    try:
        book_appointment_web(
            session['customer']['Patient_id'],
            data.get('doctor_id'),
            data.get('doctor_name'),
            data.get('date'),
            data.get('slot')
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/show_appointments')
def show_appointments():
    if 'customer' not in session:
        return redirect(url_for('login'))
    appointments = get_patient_appointments(session['customer']['Patient_id'])
    return render_template('show_appointments.html', appointments=appointments)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)