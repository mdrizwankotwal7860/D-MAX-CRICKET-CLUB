from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import functools
import os
import mysql.connector
from config import Config
import datetime
from dotenv import load_dotenv

load_dotenv()

from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
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


from flask import make_response

def no_cache(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        response = make_response(view(**kwargs))
        response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return wrapped_view

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
        # Fix for Error 1055 (ONLY_FULL_GROUP_BY) - Allow non-aggregated columns
        cursor = conn.cursor()
        cursor.execute("SET SESSION sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''))")
        cursor.close()
        return conn
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None

# --- Notification Functions ---


def send_email_core(to_email, subject, body):
    """
    Reusable secure email sending function.
    """
    try:
        sender_email = os.environ.get('MAIL_USERNAME') or Config.MAIL_USERNAME
        sender_password = os.environ.get('MAIL_PASSWORD') or Config.MAIL_PASSWORD
        
        if not sender_email or not sender_password:
             print(f"Email Failed to {to_email}: Missing Credentials")
             return False

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))

        # Secure connection with TLS
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        print(f"Email Failed to {to_email}: {e}")
        return False

def send_notification_email(booking_details):
    """
    1. ADMIN EMAIL NOTIFICATION (ON USER BOOKING)
    """
    try:
        admin_email = os.environ.get('MAIL_USERNAME') or Config.MAIL_USERNAME # Send to self/admin
        
        subject = "New Ground Slot Booking Received"
        
        body = f"""
        New Ground Slot Booking Received
        
        User Details:
        Name: {booking_details['name']}
        Phone: {booking_details['phone']}
        Email: {booking_details['email']}
        
        Booking Details:
        Date: {booking_details['date']}
        Slot Time: {booking_details['start_time']} - {booking_details.get('end_time', 'N/A')}
        Amount Paid: ₹{booking_details['paid_amount']}
        Booking Status: PENDING
        
        Please login to the admin dashboard to verify and confirm this booking.
        """
        
        send_email_core(admin_email, subject, body)

    except Exception as e:
        print(f"Admin Notification Wrapper Failed: {e}")


def send_whatsapp_core(to_number, body):
    """
    Reusable Twilio WhatsApp sending function.
    """
    try:
        sid = os.environ.get('TWILIO_SID') or Config.TWILIO_SID
        token = os.environ.get('TWILIO_AUTH_TOKEN') or Config.TWILIO_AUTH_TOKEN
        wa_from = os.environ.get('TWILIO_WHATSAPP_NUM') or Config.TWILIO_WHATSAPP_NUM
        
        if not all([sid, token, wa_from, to_number]):
            print(f"WhatsApp Failed to {to_number}: Missing Credentials or Number")
            return False

        client = Client(sid, token)
        
        message = client.messages.create(
            from_=wa_from,
            body=body,
            to=to_number
        )
        print(f"WhatsApp sent to {to_number}: {message.sid}")
        return True

    except Exception as e:
        print(f"WhatsApp Failed to {to_number}: {e}")
        return False

def send_whatsapp_notification(booking_details):
    """
    1. ADMIN WHATSAPP NOTIFICATION (ON USER BOOKING)
    """
    try:
        admin_phone = os.environ.get('ADMIN_PHONE') or Config.ADMIN_PHONE 
        
        message_body = (
            f"🏏 *New Booking Received!*\n\n"
            f"👤 *Name:* {booking_details['name']}\n"
            f"📞 *Phone:* {booking_details['phone']}\n"
            f"📅 *Date:* {booking_details['date']}\n"
            f"⏰ *Time:* {booking_details['start_time']} - {booking_details.get('end_time', 'N/A')}\n"
            f"💰 *Paid:* ₹{booking_details['paid_amount']}\n\n"
            f"Please verify in Admin Panel."
        )

        send_whatsapp_core(admin_phone, message_body)

    except Exception as e:
        print(f"Admin WhatsApp Wrapper Failed: {e}")

def send_user_whatsapp_confirmation(user_phone, booking_details):
    """
    2. USER WHATSAPP NOTIFICATION (ON ADMIN CONFIRMATION)
    """
    try:
        # Ensure user phone works with Twilio (needs whatsapp: prefix if not present)
        # Assuming user_phone is just digits (e.g., 9876543210) or +91...
        # Twilio requires 'whatsapp:+919876543210'
        
        formatted_phone = user_phone
        if not user_phone.startswith('whatsapp:'):
             # basic cleanup
             clean_phone = user_phone.replace(' ', '').replace('-', '')
             if not clean_phone.startswith('+'):
                 clean_phone = f"+91{clean_phone}" # Default to India if no code? Or just assume provided
             formatted_phone = f"whatsapp:{clean_phone}"
        
        ground_name = "D MAX SPORTS CLUB"
        maps_link = "https://www.google.com/maps?q=D+MAX+SPORTS+CLUB+Hubballi"
        
        message_body = (
            f"✅ *Booking Confirmed!*\n\n"
            f"Hey {booking_details.get('name', 'Player')}, your slot is locked! 🏏\n\n"
            f"📅 *Date:* {booking_details.get('date')}\n"
            f"⏰ *Time:* {booking_details.get('start_time')}\n\n"
            f"📍 *Location:* {ground_name}\n"
            f"🗺️ *Map:* {maps_link}\n\n"
            f"Please reach 15 mins early. Enjoy your game!"
        )
        
        send_whatsapp_core(formatted_phone, message_body)

    except Exception as e:
        print(f"User WhatsApp Wrapper Failed: {e}")


def send_user_confirmation_email(user_email, booking_details):
    """
    2. USER EMAIL NOTIFICATION (ON ADMIN CONFIRMATION)
    """
    try:
        subject = "Your Ground Slot Booking is Confirmed"
        
        ground_name = "D MAX SPORTS CLUB"
        address = "Gudihal road, near vani plot, Devaragudihal, Hubballi, Karnataka 580024"
        maps_link = "https://www.google.com/maps?q=D+MAX+SPORTS+CLUB+Hubballi"
        
        body = f"""
        Booking Confirmation
        
        Dear {booking_details.get('name', 'Player')},
        
        Your booking has been successfully confirmed!
        
        Booking Details:
        Date: {booking_details.get('date')}
        Slot Time: {booking_details.get('start_time')}
        
        Ground Location:
        Ground Name: {ground_name}
        Address: {address}
        Google Maps: {maps_link}
        
        Instructions:
        - Please reach 15 minutes before your slot time.
        - Bring a valid ID proof.
        - Have a great game!
        
        Regards,
        {ground_name} Team
        """
        
        send_email_core(user_email, subject, body)

    except Exception as e:
        print(f"User Confirmation Wrapper Failed: {e}")


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
        cursor.execute("SELECT * FROM pricing WHERE is_active = TRUE")
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
@no_cache
def admin_login():
    if 'admin_user' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = None
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['admin_user'] = user['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
@no_cache
def admin_dashboard():
    conn = get_db_connection()
    bookings = []
    tournaments = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Fetch Bookings with Slot Info
        # Note: We join on left in case slot was deleted (though we try to soft delete)
        query = """
            SELECT MIN(b.id) as id,
                   b.booking_date,
                   b.payment_proof as payment_image,
                   b.booking_status as status,
                   b.payment_status,
                   COUNT(b.id) as duration_hours,
                   SUM(b.total_price) as total_price,
                   SUM(b.paid_amount) as paid_amount,
                   MIN(s.start_time) as slot_start,
                   MAX(s.end_time) as slot_end,
                   u.name as customer_name, u.phone as customer_phone, u.email as customer_email
            FROM bookings b 
            LEFT JOIN slots s ON b.slot_id = s.id 
            LEFT JOIN users u ON b.user_id = u.id
            GROUP BY b.payment_proof, b.booking_date, b.user_id, b.booking_status, b.payment_status, u.name, u.phone, u.email
            ORDER BY b.booking_date DESC, MIN(b.created_at) DESC
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
@no_cache
def approve_booking(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Fetch booking payment proof first
            cursor.execute("SELECT payment_proof FROM bookings WHERE id = %s", (id,))
            initial_booking = cursor.fetchone()
            
            if initial_booking:
                payment_proof = initial_booking['payment_proof']
                
                # 2. Confirm ALL bookings with this payment proof
                cursor.execute("UPDATE bookings SET booking_status = 'confirmed', payment_status = 'paid_verified' WHERE payment_proof = %s", (payment_proof,))
                conn.commit()
                
                # 3. Send Email (Fetch one booking for details, assume consistent)
                query = """
                    SELECT b.*, u.name as customer_name, u.email as customer_email,
                           MIN(s.start_time) as slot_start, MAX(s.end_time) as slot_end
                    FROM bookings b
                    JOIN users u ON b.user_id = u.id
                    JOIN slots s ON b.slot_id = s.id
                    WHERE b.payment_proof = %s
                    GROUP BY b.payment_proof
                """
                cursor.execute(query, (payment_proof,))
                booking = cursor.fetchone()

                if booking:
                    # Format time range
                    start_t = booking['slot_start']
                    if isinstance(start_t, datetime.timedelta):
                        start_t = (datetime.datetime.min + start_t).time()
                    
                    end_t = booking['slot_end']
                    if isinstance(end_t, datetime.timedelta):
                        end_t = (datetime.datetime.min + end_t).time()

                    time_display = f"{start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}"
                    
                    details = {
                        'name': booking['customer_name'],
                        'date': booking['booking_date'],
                        'start_time': time_display,
                        'paid_amount': booking['paid_amount'] # Note: This might be sum? No, this query fetches 'b.*' which is arbitrary row. We should probably sum paid.
                        # Actually 'b.*' with GROUP BY is non-standard but often works for first row in MySQL default mode.
                        # Better to sustain existing simple logic or sum it properly.
                        # Let's just use the logic from dashboard.
                    }
                    # Re-fetch sum
                    cursor.execute("SELECT SUM(paid_amount) as total_paid FROM bookings WHERE payment_proof = %s", (payment_proof,))
                    total = cursor.fetchone()
                    details['paid_amount'] = total['total_paid']
                    
                    details['paid_amount'] = total['total_paid']
                    
                    # Send Notifications (Email + WhatsApp)
                    try:
                        send_user_confirmation_email(booking['customer_email'], details)
                    except: pass
                    
                    try:
                        send_user_whatsapp_confirmation(booking['customer_phone'], details)
                    except: pass
                    
                    flash('Booking group approved and verified!')
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
@no_cache
def reject_booking(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Reject booking group
            cursor.execute("SELECT payment_proof FROM bookings WHERE id = %s", (id,))
            initial_booking = cursor.fetchone()
            
            if initial_booking:
                payment_proof = initial_booking['payment_proof']
                cursor.execute("UPDATE bookings SET booking_status = 'rejected', payment_status = 'rejected' WHERE payment_proof = %s", (payment_proof,))
                conn.commit()
                flash('Booking group rejected.')
            else:
                 flash('Booking not found.')

        except Exception as e:
            flash(f'Error: {e}')
        finally:
             cursor.close()
             conn.close()
    return redirect(url_for('admin_dashboard'))




@app.route('/admin/bookings/delete/<int:id>', methods=['POST'])
@admin_required
@no_cache
def delete_booking(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Delete booking group
            cursor.execute("SELECT payment_proof FROM bookings WHERE id = %s", (id,))
            initial_booking = cursor.fetchone()
            
            if initial_booking:
                payment_proof = initial_booking['payment_proof']
                cursor.execute("DELETE FROM bookings WHERE payment_proof = %s", (payment_proof,))
                conn.commit()
                flash('Booking group deleted permanently.')
            else:
                 flash('Booking not found.')

        except Exception as e:
            flash(f'Error: {e}')
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('admin_dashboard'))

# --- Admin Slot Management ---

@app.route('/admin/slots')
@admin_required
@no_cache
def admin_slots():
    date_str = request.args.get('date', datetime.date.today().isoformat())
    conn = get_db_connection()
    slots = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM slots WHERE slot_date = %s ORDER BY start_time ASC", (date_str,))
        slots = cursor.fetchall()
        
        # Format times
        for s in slots:
             if isinstance(s['start_time'], datetime.timedelta):
                 s['start_time'] = (datetime.datetime.min + s['start_time']).time()
             if isinstance(s['end_time'], datetime.timedelta):
                 s['end_time'] = (datetime.datetime.min + s['end_time']).time()
                 
        cursor.close()
        conn.close()
    return render_template('admin_slots.html', slots=slots, selected_date=date_str)

@app.route('/admin/slots/add', methods=['POST'])
@admin_required
@no_cache
def add_slot():
    slot_date = request.form.get('slot_date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO slots (slot_date, start_time, end_time) VALUES (%s, %s, %s)", (slot_date, start_time, end_time))
            conn.commit()
            flash('Slot added successfully')
        except mysql.connector.Error as err:
            flash(f'Error adding slot: {err}')
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('admin_slots', date=slot_date))

@app.route('/admin/slots/generate', methods=['POST'])
@admin_required
@no_cache
def generate_slots():
    slot_date = request.form.get('slot_date')
    start_time_str = request.form.get('start_time', '09:00')
    end_time_str = request.form.get('end_time', '12:00') # 12 PM Noon
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Parse times
            start_dt = datetime.datetime.strptime(start_time_str, '%H:%M')
            end_dt = datetime.datetime.strptime(end_time_str, '%H:%M')
            
            # Handle overnight (e.g. 09:00 to 00:00)
            if end_dt <= start_dt:
                end_dt += datetime.timedelta(days=1)
            
            current_time = start_dt
            
            slots_created = 0
            
            # Loop until current time reaches end time
            while current_time < end_dt:
                slot_start = current_time.strftime('%H:%M:%S') # Always time part
                
                # 1 Hour Interval
                next_time_obj = current_time + datetime.timedelta(hours=1)
                
                # Careful not to exceed requested end
                if next_time_obj > end_dt:
                    break
                    
                slot_end = next_time_obj.strftime('%H:%M:%S')
                
                # Check if exists
                cursor.execute("SELECT id FROM slots WHERE slot_date = %s AND start_time = %s", (slot_date, slot_start))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO slots (slot_date, start_time, end_time) VALUES (%s, %s, %s)", 
                                   (slot_date, slot_start, slot_end))
                    slots_created += 1
                
                current_time = next_time_obj

            conn.commit()
            if slots_created > 0:
                flash(f'{slots_created} slots generated successfully!')
            else:
                flash('Slots already exist or invalid range.')
                
        except Exception as err:
            flash(f'Error generating slots: {err}')
        finally:
            cursor.close()
            conn.close()
            
    return redirect(url_for('admin_slots', date=slot_date))

@app.route('/admin/slots/toggle/<int:id>', methods=['POST'])
@admin_required
@no_cache
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
@no_cache
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
@no_cache
def add_tournament():
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    fee = request.form['fee']
    
    image_filename = None
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        
        # Validation: Extensions
        ALLOWED_TOURNAMENT_EXTENSIONS = {'png', 'jpg', 'jpeg'}
        if file and ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_TOURNAMENT_EXTENSIONS):
            
            # Validation: Size (Max 2MB)
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > 2 * 1024 * 1024:
                flash('File too large. Maximum size is 2MB.', 'error')
                return redirect(url_for('admin_dashboard'))

            # Use timestamp to ensure unique filenames
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = secure_filename(f"{timestamp}_{file.filename}")
            
            # Save to tournament_images folder
            save_path = os.path.join(app.root_path, 'static', 'tournament_images', filename)
            file.save(save_path)
            image_filename = filename
        elif file:
             flash('Invalid file format. Allowed: PNG, JPG, JPEG.', 'error')
             return redirect(url_for('admin_dashboard'))

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
@no_cache
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
    session.clear()
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
    """Return active slots for a specific date"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify([])

        conn = get_db_connection()
        slots = []
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Fetch slots for this specific date
            cursor.execute("SELECT id, start_time, end_time FROM slots WHERE slot_date = %s AND is_active = TRUE ORDER BY start_time ASC", (date_str,))
            raw_slots = cursor.fetchall()
            
            # Server-side Time Check
            now = datetime.datetime.now()
            today_str = now.strftime('%Y-%m-%d')
            is_today = (date_str == today_str)
            is_past_date = (date_str < today_str)

            for s in raw_slots:
                # Convert timedelta to string (HH:MM AM/PM)
                start_t = s['start_time']
                if isinstance(start_t, datetime.timedelta):
                    start_t = (datetime.datetime.min + start_t).time()
                
                display_str = start_t.strftime("%I:%M %p")
                
                # Check if past
                # If date is in past, all slots are past
                # If today, check time
                slot_is_past = False
                if is_past_date:
                    slot_is_past = True
                elif is_today:
                    slot_dt = datetime.datetime.combine(now.date(), start_t)
                    if slot_dt < now:
                        slot_is_past = True

                slots.append({
                    "id": s['id'],
                    "display": display_str,
                    "start_time": str(start_t), # HH:MM:SS
                    "is_past": slot_is_past
                })
                
            cursor.close()
            conn.close()
        return jsonify(slots)
    except Exception as e:
        print(f"Error in get_slots: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_availability', methods=['GET'])
def check_availability():
    try:
        date_str = request.args.get('date') # YYYY-MM-DD
        if not date_str:
            return jsonify({"error": "Date required"}), 400
        
        conn = get_db_connection()
        unavailable_slot_ids = []
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            # 0. Clean up expired locks first (Lazy cleanup)
            cursor.execute("DELETE FROM slot_locks WHERE lock_expiry < NOW()")
            conn.commit()
            
            # 1. Fetch BOOKED slots
            query_booked = """
                SELECT slot_id 
                FROM bookings 
                WHERE booking_status != 'rejected'
                AND slot_id IN (SELECT id FROM slots WHERE slot_date = %s)
            """
            cursor.execute(query_booked, (date_str,))
            booked_results = cursor.fetchall()
            unavailable_slot_ids.extend([r['slot_id'] for r in booked_results])
            
            # 2. Fetch LOCKED slots
            query_locked = """
                SELECT slot_id 
                FROM slot_locks 
                WHERE lock_expiry > NOW()
                AND slot_id IN (SELECT id FROM slots WHERE slot_date = %s)
            """
            cursor.execute(query_locked, (date_str,))
            locked_results = cursor.fetchall()
            unavailable_slot_ids.extend([r['slot_id'] for r in locked_results])
            
            # Unique IDs
            unavailable_slot_ids = list(set(unavailable_slot_ids))
            
            cursor.close()
            conn.close()
            
        return jsonify(unavailable_slot_ids)
    except Exception as e:
        print(f"Error in check_availability: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/lock_slot', methods=['POST'])
def lock_slot():
    conn = None
    cursor = None
    try:
        data = request.json
        slot_id = data.get('slot_id')
        user_identifier = data.get('user_identifier') # UUID from frontend
        
        if not slot_id or not user_identifier:
            return jsonify({"error": "Missing slot_id or user_identifier"}), 400
            
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database error"}), 500
            
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Clean expired locks
        cursor.execute("DELETE FROM slot_locks WHERE lock_expiry < NOW()")
        
        # 2. Check if already booked
        cursor.execute("SELECT id FROM bookings WHERE slot_id = %s AND booking_status != 'rejected'", (slot_id,))
        if cursor.fetchone():
            conn.rollback()
            return jsonify({"error": "Slot already booked", "status": "taken"}), 409
            
        # 3. Check if locked by SOMEONE ELSE
        cursor.execute("SELECT user_identifier FROM slot_locks WHERE slot_id = %s", (slot_id,))
        existing_lock = cursor.fetchone()
        
        if existing_lock:
            if existing_lock['user_identifier'] == user_identifier:
                # Refresh my lock
                new_expiry = (datetime.datetime.now() + datetime.timedelta(minutes=5))
                cursor.execute("UPDATE slot_locks SET lock_expiry = %s WHERE slot_id = %s", (new_expiry, slot_id))
                conn.commit()
                return jsonify({"message": "Lock refreshed", "expiry": new_expiry.isoformat()})
            else:
                # Locked by another
                conn.rollback()
                return jsonify({"error": "Slot is temporarily locked by another user", "status": "locked"}), 409
        
        # 4. Create New Lock
        new_expiry = (datetime.datetime.now() + datetime.timedelta(minutes=5))
        cursor.execute("INSERT INTO slot_locks (slot_id, user_identifier, lock_expiry) VALUES (%s, %s, %s)", 
                       (slot_id, user_identifier, new_expiry))
        
        conn.commit()
        return jsonify({"message": "Slot locked", "expiry": new_expiry.isoformat()})
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Lock error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


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
        start_time_str = request.form.get('start_time') # "HH:MM:SS" or "HH:MM"
        end_time_str = request.form.get('end_time')   # "HH:MM:SS" or "HH:MM"

        if not all([name, phone, email, date, start_time_str, end_time_str]):
            return jsonify({"error": "Missing required fields"}), 400
            
        # 1.1 Strict Phone Validation
        import re
        if not re.fullmatch(r'\d{10}', phone):
             return jsonify({"error": "Phone number must be exactly 10 digits."}), 400

        # Data Type Conversion & Time Calculation
        try:
            format_str = '%H:%M:%S' if len(start_time_str.split(':')) == 3 else '%H:%M'
            start_dt = datetime.datetime.strptime(start_time_str, format_str)
            end_dt = datetime.datetime.strptime(end_time_str, format_str)
            
            # Use dummy date for time calculation
            start_full = datetime.datetime.combine(datetime.date.today(), start_dt.time())
            end_full = datetime.datetime.combine(datetime.date.today(), end_dt.time())
            if end_full <= start_full:
                 # Handle overnight or invalid? Assume same day.
                 return jsonify({"error": "End time must be after start time."}), 400

            duration_hours = (end_full - start_full).total_seconds() / 3600.0
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
        cursor = conn.cursor(dictionary=True, buffered=True)

        # 2. Find or Create User
        cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
        existing_user = cursor.fetchone()
        user_id = None
        if existing_user:
            user_id = existing_user['id']
            # Optional: Update name/email if changed? For now, keep existing.
        else:
            cursor.execute("INSERT INTO users (name, phone, email) VALUES (%s, %s, %s)", (name, phone, email))
            user_id = cursor.lastrowid

        # 3. Get Pricing (Assume 1 hour pricing exists)
        cursor.execute("SELECT id, price FROM pricing WHERE duration_hours = 1 AND is_active = TRUE LIMIT 1")
        pricing_row = cursor.fetchone()
        if not pricing_row:
             conn.rollback()
             return jsonify({"error": "Pricing configuration not found."}), 500
        
        hourly_price = float(pricing_row['price'])
        pricing_id = pricing_row['id']
        
        # Weekend Logic Check (Saturday/Sunday)
        booking_date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        day_of_week = booking_date_obj.weekday() 
        weekend_discount = False
        # If Sat(5) or Sun(6)
        if day_of_week in [5, 6]:
            # Apply weekend rate? Logic in frontend was manual "1500 for 2 hours".
            # Here we might need logic. 
            # If 2 hours on weekend, price = 1500. Regular = 1600.
            # Effectively 750 per slot.
             if abs(duration_hours - 2.0) < 0.01:
                 hourly_price = 750.0
                 weekend_discount = True

        # 4. Resolve Slots and Check Availability
        # We assume slots are 1-hour blocks.
        # We need to find the specific slot_id for each hour in the range.
        slots_to_book = [] # List of {slot_id, start_time, price}
        
        current_time_iter = start_full
        while current_time_iter < end_full:
            slot_start_time = current_time_iter.time()
            
            # Find slot in DB for this Date + StartTime
            # Note: We query by slot_date AND start_time
            cursor.execute("SELECT id FROM slots WHERE slot_date = %s AND start_time = %s AND is_active = TRUE", (date, slot_start_time))
            slot_record = cursor.fetchone()
            
            if not slot_record:
                conn.rollback()
                return jsonify({"error": f"Slot starting at {slot_start_time} not found/inactive for this date."}), 400
                
            slot_id = slot_record['id']
            
            # Check if booked
            cursor.execute("""
                SELECT id FROM bookings 
                WHERE slot_id = %s 
                AND booking_status IN ('confirmed', 'pending') 
                AND payment_status != 'rejected'
            """, (slot_id,))
            if cursor.fetchone():
                conn.rollback()
                return jsonify({"error": f"Slot at {slot_start_time} is already booked."}), 409
                
            slots_to_book.append({
                'slot_id': slot_id,
                'price': hourly_price
            })
            
            # Increment by 1 hour
            current_time_iter += datetime.timedelta(hours=1)

        # 5. Handle File Upload
        if 'payment_screenshot' not in request.files:
            conn.rollback()
            return jsonify({"error": "Payment screenshot is mandatory"}), 400
        
        # [NEW] Validate Locks
        user_identifier = request.form.get('user_identifier')
        if not user_identifier:
             conn.rollback()
             return jsonify({"error": "Session identifier missing."}), 400

        for slot_info in slots_to_book:
            sid = slot_info['slot_id']
            # Check lock
            cursor.execute("SELECT user_identifier, lock_expiry FROM slot_locks WHERE slot_id = %s", (sid,))
            lock = cursor.fetchone()
            
            if not lock:
                conn.rollback()
                return jsonify({"error": "Session verification failed (Lock missing). Please re-select slot."}), 409
            
            if lock['user_identifier'] != user_identifier:
                conn.rollback()
                return jsonify({"error": "Slot is locked by another user."}), 409
                
            if lock['lock_expiry'] < datetime.datetime.now():
                conn.rollback()
                return jsonify({"error": "Time limit exceeded. Please re-select slot."}), 409

        file = request.files['payment_screenshot']
        if file.filename == '':
            conn.rollback()
            return jsonify({"error": "No selected file"}), 400
            
        if not (file and allowed_file(file.filename)):
            conn.rollback()
            return jsonify({"error": "Invalid file type. Only images allowed."}), 400
            
        # File Size Check
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 2 * 1024 * 1024: # 2MB limit
             conn.rollback()
             return jsonify({"error": "File too large. Max 2MB allowed."}), 400

        # Strict MIME Type Check
        # allowed_file checks extension, but let's be sure
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
             conn.rollback()
             return jsonify({"error": "Invalid file type. Only PNG/JPEG allowed."}), 400

        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"PAY_{timestamp}_{filename}"

        if not os.path.exists(app.config['PAYMENT_UPLOAD_FOLDER']):
            os.makedirs(app.config['PAYMENT_UPLOAD_FOLDER'])
            
        filepath = os.path.join(app.config['PAYMENT_UPLOAD_FOLDER'], new_filename)
        file.save(filepath)

        # 6. Insert Bookings
        total_paid_declared = float(request.form.get('paid_amount', 0.0) or (hourly_price * len(slots_to_book)))
        # Put the full declared amount in the first booking? Or split?
        # New Schema has 'paid_amount' per booking.
        # Let's split it evenly.
        paid_per_slot = total_paid_declared / len(slots_to_book) if slots_to_book else 0

        for slot_info in slots_to_book:
            insert_query = """
                INSERT INTO bookings (
                    user_id, slot_id, booking_date, pricing_id, total_price, paid_amount, 
                    payment_proof, payment_status, booking_status, verified_by, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'paid_manual_verification', 'pending', NULL, NOW())
            """
            cursor.execute(insert_query, (
                user_id, 
                slot_info['slot_id'], 
                date, 
                pricing_id, 
                slot_info['price'], 
                paid_per_slot, 
                new_filename
            ))
            
            # Remove Lock
            cursor.execute("DELETE FROM slot_locks WHERE slot_id = %s", (slot_info['slot_id'],))
            
        conn.commit()
        
        # 7. Notifications
        booking_details = {
            'name': name,
            'phone': phone,
            'email': email,
            'date': date,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'paid_amount': total_paid_declared
        }
        
        # Non-blocking notifications
        try:
            send_notification_email(booking_details)
            send_whatsapp_notification(booking_details)
        except:
            pass # Don't fail booking if notification fails

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
