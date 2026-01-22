from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import functools
import os
import mysql.connector
from config import Config
import datetime
from dotenv import load_dotenv

load_dotenv()

from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folders exist
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
PAYMENT_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'payment_proofs')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PAYMENT_UPLOAD_FOLDER'] = PAYMENT_UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'admin_user' not in session:
            return redirect(url_for('admin_login'))
        return view(**kwargs)
    return wrapped_view

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None

# --- Notification Functions ---

def send_notification_email(booking_details):
    try:
        sender_email = os.environ.get('MAIL_USERNAME') or Config.MAIL_USERNAME
        sender_password = os.environ.get('MAIL_PASSWORD') or Config.MAIL_PASSWORD
        admin_email = sender_email # Send to self/admin

        if not sender_email or not sender_password:
             print("Email Notification Failed: Missing Credentials")
             return

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = admin_email
        msg['Subject'] = f"New Slot Booking - {booking_details['name']}"

        body = f"""
        New Booking Received!
        
        Name: {booking_details['name']}
        Phone: {booking_details['phone']}
        Email: {booking_details['email']}
        Date: {booking_details['date']}
        Slot Time: {booking_details['start_time']}
        Amount Paid: {booking_details['paid_amount']}
        
        Please login to the admin panel to verify the payment.
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {admin_email}")

    except Exception as e:
        print(f"Email Notification Failed: {e}")

def send_whatsapp_notification(booking_details):
    try:
        sid = os.environ.get('TWILIO_SID') or Config.TWILIO_SID
        token = os.environ.get('TWILIO_AUTH_TOKEN') or Config.TWILIO_AUTH_TOKEN
        wa_from = os.environ.get('TWILIO_WHATSAPP_NUM') or Config.TWILIO_WHATSAPP_NUM
        admin_phone = os.environ.get('ADMIN_PHONE') or Config.ADMIN_PHONE # e.g., 'whatsapp:+919876543210'

        if not all([sid, token, wa_from, admin_phone]):
            print("WhatsApp Notification Failed: Missing Credentials")
            return

        client = Client(sid, token)
        
        message_body = (
            f"🏏 *New Slot Booked!*\n\n"
            f"👤 *Name:* {booking_details['name']}\n"
            f"📞 *Phone:* {booking_details['phone']}\n"
            f"📅 *Date:* {booking_details['date']}\n"
            f"⏰ *Time:* {booking_details['start_time']}\n\n"
            f"Please verify payment in Admin Panel."
        )

        message = client.messages.create(
            from_=wa_from,
            body=message_body,
            to=admin_phone
        )
        print(f"WhatsApp sent: {message.sid}")

    except Exception as e:
        print(f"WhatsApp Notification Failed: {e}")



def send_user_confirmation_email(user_email, booking_details):
    try:
        sender_email = os.environ.get('MAIL_USERNAME') or Config.MAIL_USERNAME
        sender_password = os.environ.get('MAIL_PASSWORD') or Config.MAIL_PASSWORD

        if not sender_email or not sender_password:
             print("User Email Notification Failed: Missing Credentials")
             return

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = "Booking Confirmed! - Box Cricket Arena"

        body = f"""
        Hey {booking_details.get('name', 'Player')},
        
        Your slot is booked! You can come and play.
        
        Booking Details:
        Date: {booking_details.get('date')}
        Time: {booking_details.get('start_time')}
        Amount Paid: {booking_details.get('paid_amount')}
        
        See you on the field!
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Confirmation email sent to {user_email}")

    except Exception as e:
        print(f"User Email Notification Failed: {e}")


# --- Routes for Pages ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/pricing')
def pricing():
    conn = get_db_connection()
    pricing_items = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pricing_config WHERE is_active = TRUE")
        pricing_items = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('pricing.html', pricing=pricing_items)

@app.route('/tournaments')
def tournaments():
    conn = get_db_connection()
    tournaments = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tournaments ORDER BY event_date ASC")
        tournaments = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('tournaments.html', tournaments=tournaments)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        if not name or not email or not message:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('contact'))
            
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)', (name, email, message))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('contact'))
            
    return render_template('contact.html')

# --- Admin Routes ---

@app.route('/admin')
def admin_root():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = None
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM admins WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
        
        if user:
            session['admin_user'] = user['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    bookings = []
    tournaments = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Fetch Bookings with Slot Info
        # Note: We join on left in case slot was deleted (though we try to soft delete)
        query = """
            SELECT b.*, s.start_time as slot_start, s.end_time as slot_end 
            FROM bookings b 
            LEFT JOIN slots s ON b.slot_id = s.id 
            ORDER BY b.booking_date DESC, b.created_at DESC
        """
        cursor.execute(query)
        bookings = cursor.fetchall()
        
        for b in bookings:
            # Format times for display
            if b.get('slot_start'):
                # Assuming timedelta or time object, convert to string
                t = b['slot_start']
                # Handle timedelta (mysql-connector sometimes returns these for TIME cols)
                if isinstance(t, datetime.timedelta):
                    total_seconds = int(t.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    b['start_time'] = f"{hours:02}:{minutes:02}"
                else:
                     b['start_time'] = str(t)
            
            # Format created_at if exists
            if b.get('created_at'):
                b['created_at'] = b['created_at'].strftime('%Y-%m-%d %H:%M')

        # Fetch Tournaments (with registration counts)
        cursor.execute("""
            SELECT t.*, COUNT(tr.id) as registration_count 
            FROM tournaments t 
            LEFT JOIN tournament_registrations tr ON t.id = tr.tournament_id 
            GROUP BY t.id
        """)
        tournaments = cursor.fetchall()
        # Fetch Contact Messages
        cursor.execute("SELECT * FROM contact_messages ORDER BY sent_at DESC LIMIT 10")
        contact_messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
    return render_template('admin_dashboard.html', bookings=bookings, tournaments=tournaments, contact_messages=contact_messages)

@app.route('/admin/bookings/approve/<int:id>', methods=['POST'])
@admin_required
def approve_booking(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Fetch booking details first
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (id,))
            booking = cursor.fetchone()
            
            if booking:
                # 2. Confirm booking
                cursor.execute("UPDATE bookings SET status = 'CONFIRMED', payment_status = 'paid_verified' WHERE id = %s", (id,))
                conn.commit()
                
                # 3. Send Email
                # Need to formatting time/date for email
                start_time_display = str(booking['start_time'])
                if isinstance(booking['start_time'], datetime.timedelta):
                     # Convert to HH:MM
                     total_seconds = int(booking['start_time'].total_seconds())
                     hours = total_seconds // 3600
                     minutes = (total_seconds % 3600) // 60
                     start_time_display = f"{hours:02}:{minutes:02}"
                
                details = {
                    'name': booking['customer_name'],
                    'date': booking['booking_date'],
                    'start_time': start_time_display,
                    'paid_amount': booking['paid_amount']
                }
                
                send_user_confirmation_email(booking['customer_email'], details)
                flash('Booking approved, verified, and confirmation email sent!')
            else:
                flash('Booking not found.')
                
        except Exception as e:
            flash(f'Error: {e}')
        finally:
             cursor.close()
             conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bookings/reject/<int:id>', methods=['POST'])
@admin_required
def reject_booking(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Reject booking - this frees up the slot_id for that date
            # Use 'REJECTED' for Enum
            cursor.execute("UPDATE bookings SET status = 'REJECTED', payment_status = 'rejected' WHERE id = %s", (id,))
            conn.commit()
            flash('Booking rejected.')
        except Exception as e:
            flash(f'Error: {e}')
        finally:
             cursor.close()
             conn.close()
    return redirect(url_for('admin_dashboard'))




@app.route('/admin/bookings/delete/<int:id>', methods=['POST'])
@admin_required
def delete_booking(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM bookings WHERE id = %s", (id,))
            conn.commit()
            flash('Booking deleted permanently.')
        except Exception as e:
            flash(f'Error: {e}')
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('admin_dashboard'))

# --- Admin Slot Management ---

@app.route('/admin/slots')
@admin_required
def admin_slots():
    conn = get_db_connection()
    slots = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM slots ORDER BY start_time ASC")
        slots = cursor.fetchall()
        
        # Format times
        for s in slots:
             if isinstance(s['start_time'], datetime.timedelta):
                 s['start_time'] = (datetime.datetime.min + s['start_time']).time()
             if isinstance(s['end_time'], datetime.timedelta):
                 s['end_time'] = (datetime.datetime.min + s['end_time']).time()
                 
        cursor.close()
        conn.close()
    # Create the template if not exists or render generic
    return render_template('admin_slots.html', slots=slots)

@app.route('/admin/slots/add', methods=['POST'])
@admin_required
def add_slot():
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO slots (start_time, end_time) VALUES (%s, %s)", (start_time, end_time))
            conn.commit()
            flash('Slot added successfully')
        except mysql.connector.Error as err:
            flash(f'Error adding slot: {err}')
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('admin_slots'))

@app.route('/admin/slots/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_slot(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE slots SET is_active = NOT is_active WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Slot status updated')
    return redirect(url_for('admin_slots'))

@app.route('/admin/slots/delete/<int:id>', methods=['POST'])
@admin_required
def delete_slot(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Check for bookings first? For now, try delete (FK might restrict it)
            cursor.execute("DELETE FROM slots WHERE id = %s", (id,))
            conn.commit()
            flash('Slot deleted')
        except mysql.connector.Error:
            # Likely FK constraint
            flash('Cannot delete slot with existing bookings. Disabled it instead.')
            cursor.execute("UPDATE slots SET is_active = FALSE WHERE id = %s", (id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('admin_slots'))


@app.route('/admin/tournaments/add', methods=['POST'])
@admin_required
def add_tournament():
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    fee = request.form['fee']
    
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tournaments (title, description, event_date, entry_fee, image_url) VALUES (%s, %s, %s, %s, %s)",
                       (title, description, date, fee, image_filename))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Tournament created successfully!')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/tournaments/delete/<int:id>', methods=['POST'])
@admin_required
def delete_tournament(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tournaments WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Tournament deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_user', None)
    return redirect(url_for('admin_login'))

# --- API Endpoints ---

@app.route('/api/tournaments', methods=['GET'])
def api_tournaments():
    conn = get_db_connection()
    tournaments = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tournaments ORDER BY event_date ASC")
        tournaments = cursor.fetchall()
        cursor.close()
        conn.close()
    return jsonify(tournaments)

@app.route('/api/slots', methods=['GET'])
def get_slots():
    """Return all active slots for frontend generation"""
    conn = get_db_connection()
    slots = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, start_time, end_time FROM slots WHERE is_active = TRUE ORDER BY start_time ASC")
        raw_slots = cursor.fetchall()
        
        for s in raw_slots:
            # Convert timedelta to string (HH:MM AM/PM)
            start_t = s['start_time']
            if isinstance(start_t, datetime.timedelta):
                start_t = (datetime.datetime.min + start_t).time()
            
            display_str = start_t.strftime("%I:%M %p")
            slots.append({
                "id": s['id'],
                "display": display_str,
                "start_time": str(start_t) # HH:MM:SS
            })
            
        cursor.close()
        conn.close()
    # Cache disabled for simplicity
    return jsonify(slots)

@app.route('/api/check_availability', methods=['GET'])
def check_availability():
    date_str = request.args.get('date') # YYYY-MM-DD
    if not date_str:
        return jsonify({"error": "Date required"}), 400
    
    conn = get_db_connection()
    booked_slot_ids = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Find all SLOT IDs that fall within any existing booking's time range
        # Using overlap logic: Booking (B) overlaps Slot (S) if B.start < S.end AND B.end > S.start
        query = """
            SELECT s.id 
            FROM slots s
            JOIN bookings b ON b.booking_date = %s 
            WHERE b.status IN ('PENDING', 'CONFIRMED', 'paid_enc_verified')
            AND b.start_time < s.end_time 
            AND b.end_time > s.start_time
        """
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        booked_slot_ids = [r['id'] for r in rows]
        
        cursor.close()
        conn.close()
    
    return jsonify(booked_slot_ids)

# Serializer for generating time-sensitive tokens
serializer = URLSafeTimedSerializer(app.secret_key)

@app.route('/api/initiate_payment', methods=['POST'])
def initiate_payment():
    # Generates a time-sensitive token for payment tracking.
    token = serializer.dumps({'init_time': datetime.datetime.now().isoformat()})
    return jsonify({'token': token})

@app.route('/api/book_slot', methods=['POST'])
def book_slot():
    conn = None
    cursor = None
    try:
        # 0. Validate Payment Token (Strict Time Limit)
        payment_token = request.form.get('payment_token')
        if not payment_token:
            return jsonify({"error": "Payment token missing. Please restart payment timer."}), 400
            
        try:
            serializer.loads(payment_token, max_age=300)
        except SignatureExpired:
             return jsonify({"error": "Payment time limit exceeded (5 mins). Please reload and try again."}), 400
        except BadTimeSignature:
             return jsonify({"error": "Invalid payment token."}), 400

        # 1. Validate Form Data
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        date = request.form.get('date')
        # We now accept start_time and end_time directly, OR derived from slots
        # Front end should send range. For simplicity, let's assume it sends start_slot_id and end_slot_id
        # OR better: start_time and end_time strings.
        # Let's stick to the plan: "Slots are range-based". 
        # But to map correctly to DB, we need exact times.
        # Let's accept start_time and end_time from frontend.
        start_time_str = request.form.get('start_time') # "HH:MM:SS" or "HH:MM"
        end_time_str = request.form.get('end_time')   # "HH:MM:SS" or "HH:MM"
        paid_amount = request.form.get('paid_amount')

        if not all([name, phone, email, date, start_time_str, end_time_str, paid_amount]):
            return jsonify({"error": "Missing required fields"}), 400
            
        # 1.1 Strict Phone Validation
        import re
        if not re.fullmatch(r'\d{10}', phone):
             return jsonify({"error": "Phone number must be exactly 10 digits."}), 400

        # Data Type Conversion
        try:
            paid_amount_float = float(paid_amount)
            # Parse times
            format_str = '%H:%M:%S' if len(start_time_str.split(':')) == 3 else '%H:%M'
            start_dt = datetime.datetime.strptime(start_time_str, format_str)
            end_dt = datetime.datetime.strptime(end_time_str, format_str)
            
            # Duration calc
            duration_td = end_dt - start_dt
            duration_hours = duration_td.total_seconds() / 3600
            
            if duration_hours <= 0:
                 return jsonify({"error": "Invalid time range."}), 400
                 
        except ValueError:
             return jsonify({"error": "Invalid data format"}), 400

        # --- DB SECTION START ---
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database error"}), 500
        
        # START TRANSACTION
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # 2. Locking: Lock bookings for this date to prevent race conditions
        cursor.execute("SELECT id FROM bookings WHERE booking_date = %s FOR UPDATE", (date,))
        _ = cursor.fetchall() # Consume to avoid Unread Result
        
        # 3. Dynamic Price Calculation
        expected_price = 800.0 * duration_hours
        
        # Weekend Discount: 100 Rs off for 2 hours on Sat/Sun
        booking_date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        day_of_week = booking_date_obj.weekday() # 0=Monday, 5=Saturday, 6=Sunday
        
        if (day_of_week == 5 or day_of_week == 6) and abs(duration_hours - 2.0) < 0.01:
             expected_price = 1500.0

        # Optional: Check pricing config (if we want to support non-800 later)
        # cursor.execute("SELECT price FROM pricing_config WHERE duration_hours = 1 AND is_active = TRUE LIMIT 1")
        # res = cursor.fetchone()
        # if res:
        #    expected_price = float(res['price']) * duration_hours
        
        if abs(paid_amount_float - expected_price) > 0.01:
            conn.rollback()
            return jsonify({"error": f"Amount Mismatch. Expected {expected_price}"}), 400

        # 4. Strict Overlap Check
        # Conflict if: Existing Booking connects with New Range
        # Logic: (Existing.Start < New.End) AND (Existing.End > New.Start)
        overlap_query = """
            SELECT id FROM bookings 
            WHERE booking_date = %s 
            AND status IN ('PENDING', 'CONFIRMED', 'paid_enc_verified')
            AND (start_time < %s AND end_time > %s)
        """
        # Convert dt back to string for SQL
        s_time_sql = start_dt.time()
        e_time_sql = end_dt.time()
        
        cursor.execute(overlap_query, (date, e_time_sql, s_time_sql))
        if cursor.fetchone():
            conn.rollback()
            return jsonify({"error": "Slot range is no longer available. Please select another time."}), 409

        # 5. Handle File (Pre-upload checks)
        if 'payment_screenshot' not in request.files:
            conn.rollback()
            return jsonify({"error": "Payment screenshot is mandatory"}), 400
        
        file = request.files['payment_screenshot']
        if file.filename == '':
            conn.rollback()
            return jsonify({"error": "No selected file"}), 400
            
        if not (file and allowed_file(file.filename)):
            conn.rollback()
            return jsonify({"error": "Invalid file type. Only images allowed."}), 400
            
        # Check file size (approx check via seek, or just rely on nginx/flask limits, 
        # but here we can check Content-Length header or read blob)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 2 * 1024 * 1024: # 2MB
             conn.rollback()
             return jsonify({"error": "File too large. Max 2MB."}), 400

        # 6. Save File
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"PAY_{timestamp}_{filename}"

        if not os.path.exists(app.config['PAYMENT_UPLOAD_FOLDER']):
            os.makedirs(app.config['PAYMENT_UPLOAD_FOLDER'])
            
        filepath = os.path.join(app.config['PAYMENT_UPLOAD_FOLDER'], new_filename)
        file.save(filepath)

        # 7. Insert Booking
        # Note: 'slot_id' is less relevant now with custom ranges, but we can store the Start Slot ID for reference
        # or NULL. Let's try to find the start slot ID to keep FK happy if strict.
        # If the schema requires slot_id, we pick the slot that starts at start_time.
        cursor.execute("SELECT id FROM slots WHERE start_time = %s", (s_time_sql,))
        slot_row = cursor.fetchone()
        slot_id = slot_row['id'] if slot_row else None 
        # CAUTION: If user picks non-slot aligned time, this might be null. 
        # Assuming UI enforces slot-aligned times.
        
        insert_query = """
            INSERT INTO bookings (
                customer_name, customer_phone, customer_email, booking_date, slot_id, start_time, end_time, duration_hours, total_price, 
                status, payment_image, payment_status, payment_uploaded_at, paid_amount
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', %s, 'paid_manual_verification', NOW(), %s)
        """
        cursor.execute(insert_query, (name, phone, email, date, slot_id, s_time_sql, e_time_sql, duration_hours, expected_price, new_filename, paid_amount_float))
        conn.commit()
        
        # 8. Notifications
        booking_details = {
            'name': name,
            'phone': phone,
            'email': email,
            'date': date,
            'start_time': str(s_time_sql),
            'paid_amount': paid_amount
        }
        
        # Non-blocking notifications
        send_notification_email(booking_details)
        send_whatsapp_notification(booking_details)

        return jsonify({"message": "Booking request submitted. Waiting for verification."})

    except mysql.connector.Error as err:
        if conn: conn.rollback()
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        # cleanup
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/register_tournament', methods=['POST'])
def register_tournament():
    try:
        data = request.json
        tournament_id = data.get('tournament_id')
        team_name = data.get('team_name')
        captain_name = data.get('captain_name')
        captain_phone = data.get('captain_phone')

        if not all([tournament_id, team_name, captain_name, captain_phone]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            # Verify tournament exists
            cursor.execute("SELECT id FROM tournaments WHERE id = %s", (tournament_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({"error": "Invalid Tournament ID"}), 400

            # Insert Registration
            query = """
                INSERT INTO tournament_registrations (tournament_id, team_name, captain_name, captain_phone, status, registered_at)
                VALUES (%s, %s, %s, %s, 'PENDING', NOW())
            """
            cursor.execute(query, (tournament_id, team_name, captain_name, captain_phone))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return jsonify({"message": "Registration successful!"}), 200
        else:
            return jsonify({"error": "Database connection failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
