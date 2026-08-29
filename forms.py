import re
import datetime

def validate_booking_request(movie_id, theatre_id, show_id, ticket_count):
    errors = {}
    
    if not movie_id:
        errors["MovieID"] = "Movie selection is mandatory."
    if not theatre_id:
        errors["TheatreID"] = "Theatre selection is mandatory."
    if not show_id:
        errors["ShowID"] = "Show selection is mandatory."
        
    try:
        count = int(ticket_count)
        if count < 1:
            errors["NumberOfTickets"] = "Ticket count must be at least 1."
    except (ValueError, TypeError):
        errors["NumberOfTickets"] = "Ticket count must be a valid integer."
        
    return errors

def validate_show_date(show_date_str, show_time_str):
    errors = {}
    try:
        show_datetime = datetime.datetime.strptime(f"{show_date_str} {show_time_str}", "%Y-%m-%d %H:%M")
        if show_datetime < datetime.datetime.now():
            errors["ShowDateTime"] = "The selected show is in the past and cannot be booked."
    except Exception:
        errors["ShowDateTime"] = "Invalid show date or time format."
    return errors

def validate_contact_info(name, email, phone):
    errors = {}
    
    if not name or not name.strip():
        errors["FullName"] = "Customer Name is required."
        
    if not email or not email.strip():
        errors["Email"] = "Email address is required for sending notifications."
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors["Email"] = "Invalid email format."
        
    if phone and not re.match(r"^\+?1?[0-9\-]{7,15}$", phone.strip()):
        errors["Phone"] = "Invalid phone number format."
        
    return errors

def validate_seat_selection(selected_seats, number_of_tickets):
    errors = {}
    num_selected = len(selected_seats) if selected_seats else 0
    if num_selected != number_of_tickets:
        errors["SelectedSeats"] = f"Please select exactly {number_of_tickets} seat(s). Currently selected: {num_selected}."
    return errors
