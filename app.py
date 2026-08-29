from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os
import datetime
import uuid
import threading
import time
from database import DB_PATH, get_db_connection, init_db, seed_db
from forms import validate_booking_request, validate_contact_info, validate_seat_selection, validate_show_date

app = Flask(__name__)
app.secret_key = "cinewave_secret_key"

# Ensure DB is initialized
if not os.path.exists(DB_PATH):
    init_db()
    seed_db()

# --- Helpers ---

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    conn.close()

def get_booking_details(booking_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.*, c.FullName, c.Email, c.Phone, s.ShowDate, s.ShowTime, s.TicketPrice, s.ShowStatus, 
               m.Title as MovieTitle, t.TheatreName, sc.ScreenName
        FROM Booking b
        JOIN Customer c ON b.CustomerID = c.CustomerID
        JOIN Show s ON b.ShowID = s.ShowID
        JOIN Movie m ON s.MovieID = m.MovieID
        JOIN Theatre t ON s.TheatreID = t.TheatreID
        JOIN Screen sc ON s.ScreenID = sc.ScreenID
        WHERE b.pyID = ?
    """, (booking_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    booking = dict(row)
    
    # Get selected seats
    cur.execute("""
        SELECT SeatNumber, SeatCategory, SeatStatus 
        FROM Seat 
        WHERE BookingID = ?
    """, (booking_id,))
    booking["SelectedSeats"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return booking

# --- Business Logic & Automation Functions ---

def run_generate_booking_ref(show_id, booking_id):
    # Generates booking reference: CW-{ShowID}-{pyID}
    # Using first 8 chars of booking UUID for clean representation
    short_id = booking_id.split("-")[0]
    return f"CW-{show_id}-{short_id}".upper()

def run_update_seat_inventory(booking_id, confirm=True):
    """
    If confirm=True: decrements AvailableSeats, updates Held seats to Booked.
    If confirm=False (Release/Cancel): releases Held seats, increments AvailableSeats back.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT ShowID, NumberOfTickets FROM Booking WHERE pyID = ?", (booking_id,))
        booking = cur.fetchone()
        if not booking:
            return
        show_id, ticket_count = booking["ShowID"], booking["NumberOfTickets"]
        
        if confirm:
            # Set Held seats to Booked
            cur.execute("""
                UPDATE Seat 
                SET SeatStatus = 'Booked' 
                WHERE BookingID = ? AND SeatStatus = 'Held'
            """, (booking_id,))
            
            # Decrement Show.AvailableSeats
            cur.execute("""
                UPDATE Show 
                SET AvailableSeats = AvailableSeats - ? 
                WHERE ShowID = ?
            """, (ticket_count, show_id))
        else:
            # Revert Held/Booked seats to Available, clear BookingID
            cur.execute("""
                UPDATE Seat 
                SET SeatStatus = 'Available', BookingID = NULL 
                WHERE BookingID = ?
            """, (booking_id,))
            
            # Re-increment AvailableSeats if they were already deducted (e.g. if we are reverting confirmed)
            # Actually if we only held them in stage 2/3, we didn't decrement AvailableSeats yet (done in Stage 4)
            # Let's check the booking status to decide if we need to restore inventory
            cur.execute("SELECT BookingStatus FROM Booking WHERE pyID = ?", (booking_id,))
            b_status = cur.fetchone()["BookingStatus"]
            if b_status == "Confirmed" or b_status == "Open-InProgress":
                cur.execute("""
                    UPDATE Show 
                    SET AvailableSeats = AvailableSeats + ? 
                    WHERE ShowID = ?
                """, (ticket_count, show_id))
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error updating inventory: {e}")
    finally:
        conn.close()

def run_send_notification(booking_id, trigger_type):
    # Simulated Notifications - Creates a Notification record and prints content to console/logs
    booking = get_booking_details(booking_id)
    if not booking:
        return
        
    email = booking["Email"]
    name = booking["FullName"]
    ref = booking["BookingReference"] or booking["pyID"]
    
    # Select Correspondence text
    corr_templates = {
        "BookingRequestReceivedEmail": f"Dear {name},\n\nWe have received your booking request (ID: {ref}). Your case is in Stage 1.\n\nBest regards,\nCineWave Team",
        "NoAvailabilityEmail": f"Dear {name},\n\nWe are sorry to inform you that seats are no longer available for your selected show. Your booking has been cancelled.\n\nBest regards,\nCineWave Team",
        "ConfirmBookingRequestEmail": f"Dear {name},\n\nYour seats are temporarily held. Please confirm your booking within 30 minutes: {ref}.\n\nBest regards,\nCineWave Team",
        "BookingConfirmationEmail": f"Dear {name},\n\nBooking Confirmed! Reference: {ref}.\nMovie: {booking['MovieTitle']}\nTheatre: {booking['TheatreName']}\nScreen: {booking['ScreenName']}\nSeats: {', '.join([s['SeatNumber'] for s in booking['SelectedSeats']])}\nDate: {booking['ShowDate']} at {booking['ShowTime']}\nTotal Paid: ${booking['TotalAmount']:.2f}\n\nEnjoy your show!\nCineWave Team",
        "BookingNotConfirmedEmail": f"Dear {name},\n\nYour booking request has been declined or failed. Any temporary hold on seats has been released.\n\nBest regards,\nCineWave Team"
    }
    
    corr_body = corr_templates.get(trigger_type, f"Notification regarding booking {ref}.")
    
    # Write to database
    notification_id = str(uuid.uuid4())
    sent_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_db("""
        INSERT INTO Notification (NotificationID, BookingID, Channel, Status, SentDateTime)
        VALUES (?, ?, ?, ?, ?)
    """, (notification_id, booking_id, "Email", "Sent", sent_time))
    
    # Log the simulated email to console/logs
    print(f"\n===== SIMULATED NOTIFICATION ({trigger_type}) =====")
    print(f"TO: {email}")
    print(f"SENT AT: {sent_time}")
    print(f"CONTENT:\n{corr_body}")
    print("==================================================\n")

def check_and_expire_held_bookings():
    """
    Checks for bookings in 'Pending-Confirmation' status that have exceeded the 30-minute SLA
    and automatically reverts them to 'Resolved-NoAvailability' or 'Resolved-Declined'.
    For prototype purposes, we can check if they are older than 2 minutes (if wanted) or 30 minutes.
    Let's check for 30 minutes in production, but let's also allow a manual trigger for ease of testing.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    # Let's find bookings in Pending-Confirmation created > 30 minutes ago
    cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        SELECT pyID FROM Booking 
        WHERE BookingStatus = 'Pending-Confirmation' AND CreatedDateTime < ?
    """, (cutoff,))
    expired = [r["pyID"] for r in cur.fetchall()]
    conn.close()
    
    for b_id in expired:
        expire_booking(b_id)

def expire_booking(booking_id):
    # Release held seats
    run_update_seat_inventory(booking_id, confirm=False)
    # Revert booking status to Resolved-NoAvailability
    execute_db("""
        UPDATE Booking 
        SET BookingStatus = 'Resolved-NoAvailability' 
        WHERE pyID = ?
    """, (booking_id,))
    run_send_notification(booking_id, "BookingNotConfirmedEmail")
    print(f"SLA Expired: Booking {booking_id} has been automatically resolved to Resolved-NoAvailability.")

# Background thread for SLA check (runs every 60 seconds)
def start_sla_monitor():
    def monitor():
        while True:
            try:
                check_and_expire_held_bookings()
            except Exception as e:
                print(f"SLA Monitor error: {e}")
            time.sleep(60)
            
    t = threading.Thread(target=monitor, daemon=True)
    t.start()

start_sla_monitor()


# --- Routes ---

@app.route("/")
def home():
    # User landing page showing active movies
    movies = query_db("SELECT * FROM Movie")
    return render_template("home.html", movies=movies)

@app.route("/booking/new", methods=["GET", "POST"])
def new_booking():
    # Stage 1: Capture Booking Details & Customer Info
    if request.method == "POST":
        movie_id = request.form.get("movie_id")
        theatre_id = request.form.get("theatre_id")
        show_id = request.form.get("show_id")
        ticket_count_str = request.form.get("ticket_count")
        
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        
        # Validation rules
        errors = validate_booking_request(movie_id, theatre_id, show_id, ticket_count_str)
        contact_errors = validate_contact_info(full_name, email, phone)
        errors.update(contact_errors)
        
        if errors:
            for field, err in errors.items():
                flash(f"{field}: {err}", "danger")
            # Reload page with selections
            movies = query_db("SELECT * FROM Movie")
            theatres = query_db("SELECT * FROM Theatre")
            shows = query_db("SELECT s.*, m.Title, t.TheatreName, sc.ScreenName FROM Show s JOIN Movie m ON s.MovieID = m.MovieID JOIN Theatre t ON s.TheatreID = t.TheatreID JOIN Screen sc ON s.ScreenID = sc.ScreenID WHERE s.ShowStatus = 'Active'")
            return render_template("stage1_request.html", movies=movies, theatres=theatres, shows=shows, form_data=request.form)
            
        ticket_count = int(ticket_count_str)
        
        # Create customer record if email doesn't exist, else retrieve
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT CustomerID FROM Customer WHERE Email = ?", (email,))
        cust_row = cur.fetchone()
        if cust_row:
            customer_id = cust_row["CustomerID"]
            # Update customer details
            cur.execute("UPDATE Customer SET FullName = ?, Phone = ? WHERE CustomerID = ?", (full_name, phone, customer_id))
        else:
            customer_id = str(uuid.uuid4())
            cur.execute("INSERT INTO Customer VALUES (?, ?, ?, ?)", (customer_id, full_name, email, phone))
            
        # Create Booking case
        booking_id = str(uuid.uuid4())
        created_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Base price * ticket count for initial total amount
        cur.execute("SELECT TicketPrice FROM Show WHERE ShowID = ?", (show_id,))
        show_row = cur.fetchone()
        base_price = show_row["TicketPrice"] if show_row else 10.0
        total_amount = base_price * ticket_count
        
        cur.execute("""
            INSERT INTO Booking (pyID, CustomerID, ShowID, NumberOfTickets, TotalAmount, BookingStatus, CreatedDateTime)
            VALUES (?, ?, ?, ?, ?, 'New', ?)
        """, (booking_id, customer_id, show_id, ticket_count, total_amount, created_time))
        conn.commit()
        conn.close()
        
        run_send_notification(booking_id, "BookingRequestReceivedEmail")
        
        # Transition to Stage 2 (Availability Validation)
        return redirect(url_for("select_seats", booking_id=booking_id))
        
    movies = query_db("SELECT * FROM Movie")
    theatres = query_db("SELECT * FROM Theatre")
    shows = query_db("""
        SELECT s.*, m.Title as MovieTitle, t.TheatreName, sc.ScreenName 
        FROM Show s 
        JOIN Movie m ON s.MovieID = m.MovieID 
        JOIN Theatre t ON s.TheatreID = t.TheatreID 
        JOIN Screen sc ON s.ScreenID = sc.ScreenID 
        WHERE s.ShowStatus = 'Active'
    """)
    return render_template("stage1_request.html", movies=movies, theatres=theatres, shows=shows, form_data={})

@app.route("/booking/<booking_id>/select-seats", methods=["GET", "POST"])
def select_seats(booking_id):
    # Stage 2: Availability & Show Validation
    booking = get_booking_details(booking_id)
    if not booking:
        flash("Booking case not found.", "danger")
        return redirect(url_for("home"))
        
    show_id = booking["ShowID"]
    ticket_count = booking["NumberOfTickets"]
    
    # 2.1 Check Show Validity (When condition: IsShowValid)
    show = query_db("SELECT * FROM Show WHERE ShowID = ?", (show_id,), one=True)
    show_valid_errs = validate_show_date(show["ShowDate"], show["ShowTime"])
    if show["ShowStatus"] != "Active" or show_valid_errs:
        # Route to alternate path: Resolved-NoAvailability
        execute_db("UPDATE Booking SET BookingStatus = 'Resolved-NoAvailability' WHERE pyID = ?", (booking_id,))
        run_send_notification(booking_id, "NoAvailabilityEmail")
        flash("The selected show is no longer active or is in the past.", "danger")
        return redirect(url_for("booking_final", booking_id=booking_id))
        
    # 2.2 Check Seat Availability (When condition: IsSeatAvailable)
    available_seats_count = show["AvailableSeats"]
    if available_seats_count < ticket_count:
        # Route to alternate path: Resolved-NoAvailability
        execute_db("UPDATE Booking SET BookingStatus = 'Resolved-NoAvailability' WHERE pyID = ?", (booking_id,))
        run_send_notification(booking_id, "NoAvailabilityEmail")
        flash("Not enough seats available for this show.", "danger")
        return redirect(url_for("booking_final", booking_id=booking_id))
        
    # GET: Present seat map
    if request.method == "POST":
        selected_seat_numbers = request.form.getlist("seats")
        
        # 2.3 Present Seat Map / Selection Validation
        seat_errors = validate_seat_selection(selected_seat_numbers, ticket_count)
        if seat_errors:
            flash(seat_errors["SelectedSeats"], "danger")
            return redirect(url_for("select_seats", booking_id=booking_id))
            
        # Verify seats are still 'Available'
        conn = get_db_connection()
        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(selected_seat_numbers))
        cur.execute(f"""
            SELECT SeatNumber, SeatStatus 
            FROM Seat 
            WHERE ShowID = ? AND SeatNumber IN ({placeholders})
        """, [show_id] + selected_seat_numbers)
        seat_rows = cur.fetchall()
        
        for sr in seat_rows:
            if sr["SeatStatus"] != "Available":
                flash(f"Seat {sr['SeatNumber']} is already held or booked. Please select other seats.", "danger")
                conn.close()
                return redirect(url_for("select_seats", booking_id=booking_id))
                
        # Hold selected seats
        cur.execute(f"""
            UPDATE Seat 
            SET SeatStatus = 'Held', BookingID = ? 
            WHERE ShowID = ? AND SeatNumber IN ({placeholders})
        """, [booking_id, show_id] + selected_seat_numbers)
        
        # Calculate total amount based on categories
        # Let's say Regular = base, Premium = base * 1.2, Recliner = base * 1.5
        cur.execute(f"""
            SELECT SeatCategory FROM Seat WHERE BookingID = ?
        """, (booking_id,))
        selected_cats = [r["SeatCategory"] for r in cur.fetchall()]
        
        total_amount = 0
        base_price = show["TicketPrice"]
        for cat in selected_cats:
            if cat == "Premium":
                total_amount += base_price * 1.2
            elif cat == "Recliner":
                total_amount += base_price * 1.5
            else:
                total_amount += base_price
                
        # Update booking details and set status to 'Pending-Confirmation' (Stage 3 status)
        cur.execute("""
            UPDATE Booking 
            SET TotalAmount = ?, BookingStatus = 'Pending-Confirmation' 
            WHERE pyID = ?
        """, (total_amount, booking_id))
        
        conn.commit()
        conn.close()
        
        run_send_notification(booking_id, "ConfirmBookingRequestEmail")
        return redirect(url_for("confirm_booking", booking_id=booking_id))
        
    # Load all seats for show
    seats = query_db("SELECT * FROM Seat WHERE ShowID = ? ORDER BY SeatNumber", (show_id,))
    
    # Structure seats by row for grid rendering
    # seat numbers are like A1, A2... B1, B2...
    seats_by_row = {}
    for s in seats:
        row = s["SeatNumber"][0]
        if row not in seats_by_row:
            seats_by_row[row] = []
        seats_by_row[row].append(dict(s))
        
    return render_template("stage2_seat_selection.html", booking=booking, seats_by_row=seats_by_row, ticket_count=ticket_count)

@app.route("/booking/<booking_id>/confirm", methods=["GET", "POST"])
def confirm_booking(booking_id):
    # Stage 3: Customer Confirmation
    booking = get_booking_details(booking_id)
    if not booking or booking["BookingStatus"] != "Pending-Confirmation":
        flash("Booking case is not in the confirmation stage.", "warning")
        return redirect(url_for("home"))
        
    # Calculate simulated remaining SLA time (30 minutes from creation)
    created_time = datetime.datetime.strptime(booking["CreatedDateTime"], "%Y-%m-%d %H:%M:%S")
    elapsed = (datetime.datetime.now() - created_time).total_seconds()
    time_remaining_sec = max(0, 1800 - elapsed)
    time_remaining_min = int(time_remaining_sec // 60)
    
    if time_remaining_sec <= 0:
        expire_booking(booking_id)
        flash("Your seat hold has expired (30-minute SLA exceeded).", "danger")
        return redirect(url_for("booking_final", booking_id=booking_id))
        
    if request.method == "POST":
        action = request.form.get("action")
        if action == "confirm":
            # Set confirmation flag and transition to Stage 4 (Booking Processing)
            execute_db("""
                UPDATE Booking 
                SET ConfirmationFlag = 1, BookingStatus = 'Open-InProgress' 
                WHERE pyID = ?
            """, (booking_id,))
            return redirect(url_for("process_booking", booking_id=booking_id))
        else:
            # Revert Held seats
            run_update_seat_inventory(booking_id, confirm=False)
            execute_db("""
                UPDATE Booking 
                SET BookingStatus = 'Resolved-Declined' 
                WHERE pyID = ?
            """, (booking_id,))
            run_send_notification(booking_id, "BookingNotConfirmedEmail")
            flash("Booking request declined.", "info")
            return redirect(url_for("booking_final", booking_id=booking_id))
            
    return render_template("stage3_confirmation.html", booking=booking, time_remaining_min=time_remaining_min)

@app.route("/booking/<booking_id>/process", methods=["GET", "POST"])
def process_booking(booking_id):
    # Stage 4: Booking Processing (Internal/Simulated)
    booking = get_booking_details(booking_id)
    if not booking or booking["BookingStatus"] != "Open-InProgress":
        flash("Booking case is not in the processing stage.", "warning")
        return redirect(url_for("home"))
        
    if request.method == "POST":
        payment_status = request.form.get("payment_status")
        
        if payment_status == "success":
            # 4.1 Generate Booking Reference
            booking_ref = run_generate_booking_ref(booking["ShowID"], booking_id)
            
            # 4.2 Deduct Seat Inventory (Decrements show count, updates held to booked)
            run_update_seat_inventory(booking_id, confirm=True)
            
            # Update booking status, reference, and payment
            execute_db("""
                UPDATE Booking 
                SET BookingStatus = 'Resolved-Completed', 
                    BookingReference = ?, 
                    PaymentStatus = 'Paid' 
                WHERE pyID = ?
            """, (booking_ref, booking_id))
            
            # 5.2 Notify Customer (Stage 5 action)
            run_send_notification(booking_id, "BookingConfirmationEmail")
            
            flash("Booking processed successfully! Ticket issued.", "success")
            return redirect(url_for("booking_final", booking_id=booking_id))
        else:
            # Payment failed alternate path: Resolved-PaymentFailed
            run_update_seat_inventory(booking_id, confirm=False)
            execute_db("""
                UPDATE Booking 
                SET BookingStatus = 'Resolved-PaymentFailed', 
                    PaymentStatus = 'Failed' 
                WHERE pyID = ?
            """, (booking_id,))
            run_send_notification(booking_id, "BookingNotConfirmedEmail")
            flash("Payment processing failed. Held seats have been released.", "danger")
            return redirect(url_for("booking_final", booking_id=booking_id))
            
    return render_template("stage4_processing.html", booking=booking)

@app.route("/booking/<booking_id>/final")
def booking_final(booking_id):
    # Stage 5: Confirmed & Notified / Resolution Summary
    booking = get_booking_details(booking_id)
    if not booking:
        flash("Booking case not found.", "danger")
        return redirect(url_for("home"))
        
    # Get notifications
    notifications = query_db("SELECT * FROM Notification WHERE BookingID = ? ORDER BY SentDateTime DESC", (booking_id,))
    
    return render_template("stage5_confirmed.html", booking=booking, notifications=notifications)

# --- Staff Dashboard & Manager Portal ---

@app.route("/dashboard")
def dashboard():
    bookings = query_db("""
        SELECT b.*, c.FullName, m.Title as MovieTitle, t.TheatreName
        FROM Booking b
        JOIN Customer c ON b.CustomerID = c.CustomerID
        JOIN Show s ON b.ShowID = s.ShowID
        JOIN Movie m ON s.MovieID = m.MovieID
        JOIN Theatre t ON s.TheatreID = t.TheatreID
        ORDER BY b.CreatedDateTime DESC
    """)
    
    # Simple metrics
    stats = {}
    stats["total"] = len(bookings)
    stats["completed"] = len([b for b in bookings if b["BookingStatus"] == "Resolved-Completed"])
    stats["declined"] = len([b for b in bookings if b["BookingStatus"] == "Resolved-Declined"])
    stats["no_availability"] = len([b for b in bookings if b["BookingStatus"] == "Resolved-NoAvailability"])
    stats["payment_failed"] = len([b for b in bookings if b["BookingStatus"] == "Resolved-PaymentFailed"])
    stats["active"] = len([b for b in bookings if b["BookingStatus"] in ("New", "Pending-Availability", "Pending-Confirmation", "Open-InProgress")])
    
    return render_template("staff_dashboard.html", bookings=bookings, stats=stats)

@app.route("/dashboard/expire/<booking_id>", methods=["POST"])
def trigger_manual_expiry(booking_id):
    # Manual SLA expiry check/trigger for testing convenience
    booking = get_booking_details(booking_id)
    if booking and booking["BookingStatus"] == "Pending-Confirmation":
        expire_booking(booking_id)
        flash("Booking case manually expired by SLA rules.", "info")
    else:
        flash("Cannot expire this case status.", "warning")
    return redirect(url_for("dashboard"))

@app.route("/manager", methods=["GET", "POST"])
def manager():
    # Manager portal: shows show seat layouts and lets them add movies/shows
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_movie":
            movie_id = request.form.get("movie_id")
            title = request.form.get("title")
            genre = request.form.get("genre")
            language = request.form.get("language")
            duration = request.form.get("duration")
            rating = request.form.get("rating")
            desc = request.form.get("description")
            
            execute_db("""
                INSERT INTO Movie (MovieID, Title, Genre, Language, DurationMinutes, Rating, Description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (movie_id, title, genre, language, int(duration), rating, desc))
            flash(f"Movie '{title}' added successfully.", "success")
            
        elif action == "add_show":
            show_id = request.form.get("show_id")
            movie_id = request.form.get("movie_id")
            theatre_id = request.form.get("theatre_id")
            screen_id = request.form.get("screen_id")
            show_date = request.form.get("show_date")
            show_time = request.form.get("show_time")
            price = request.form.get("price")
            
            # Fetch total seats from screen
            screen = query_db("SELECT TotalSeats FROM Screen WHERE ScreenID = ?", (screen_id,), one=True)
            total_seats = screen["TotalSeats"] if screen else 30
            
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO Show (ShowID, MovieID, TheatreID, ScreenID, ShowDate, ShowTime, TicketPrice, TotalSeats, AvailableSeats, ShowStatus)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
            """, (show_id, movie_id, theatre_id, screen_id, show_date, show_time, float(price), total_seats, total_seats))
            
            # Generate seats for the show
            num_rows = 3 if screen_id in ("S1", "S3") else 2
            seat_records = []
            for r_idx, row_char in enumerate(["A", "B", "C"][:num_rows]):
                cat = "Regular" if row_char == "A" else ("Premium" if row_char == "B" else "Recliner")
                for col in range(1, 11):
                    seat_num = f"{row_char}{col}"
                    seat_id = f"{show_id}_{seat_num}"
                    seat_records.append((seat_id, show_id, None, seat_num, cat, "Available"))
            
            cur.executemany("INSERT INTO Seat VALUES (?, ?, ?, ?, ?, ?)", seat_records)
            conn.commit()
            conn.close()
            flash(f"Show '{show_id}' and seat inventory created successfully.", "success")
            
    movies = query_db("SELECT * FROM Movie")
    theatres = query_db("SELECT * FROM Theatre")
    screens = query_db("SELECT * FROM Screen")
    shows = query_db("""
        SELECT s.*, m.Title as MovieTitle, t.TheatreName, sc.ScreenName 
        FROM Show s 
        JOIN Movie m ON s.MovieID = m.MovieID 
        JOIN Theatre t ON s.TheatreID = t.TheatreID 
        JOIN Screen sc ON s.ScreenID = sc.ScreenID
    """)
    
    return render_template("manager_portal.html", movies=movies, theatres=theatres, screens=screens, shows=shows)

@app.route("/reset")
def reset():
    # Database reset route
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    seed_db()
    flash("Database reset to original seed data.", "success")
    return redirect(url_for("home"))


# --- Custom Template Filters ---

@app.template_filter('status_badge')
def status_badge(status):
    classes = {
        'New': 'bg-info text-dark',
        'Pending-Availability': 'bg-warning text-dark',
        'Pending-Confirmation': 'bg-warning text-dark',
        'Open-InProgress': 'bg-primary',
        'Resolved-Completed': 'bg-success',
        'Resolved-Declined': 'bg-secondary',
        'Resolved-NoAvailability': 'bg-danger',
        'Resolved-PaymentFailed': 'bg-danger'
    }
    return classes.get(status, 'bg-dark')

@app.template_filter('stage_name')
def stage_name(status):
    stages = {
        'New': 'Stage 1: Booking Request',
        'Pending-Availability': 'Stage 2: Availability Check',
        'Pending-Confirmation': 'Stage 3: Customer Confirmation',
        'Open-InProgress': 'Stage 4: Booking Processing',
        'Resolved-Completed': 'Stage 5: Confirmed & Notified',
        'Resolved-Declined': 'Declined (Terminal)',
        'Resolved-NoAvailability': 'No Availability (Terminal)',
        'Resolved-PaymentFailed': 'Payment Failed (Terminal)'
    }
    return stages.get(status, 'Unknown Stage')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
