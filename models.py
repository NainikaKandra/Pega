class Movie:
    def __init__(self, movie_id, title, genre, language, duration_minutes, rating, description):
        self.movie_id = movie_id
        self.title = title
        self.genre = genre
        self.language = language
        self.duration_minutes = duration_minutes
        self.rating = rating
        self.description = description

    def to_dict(self):
        return {
            "MovieID": self.movie_id,
            "Title": self.title,
            "Genre": self.genre,
            "Language": self.language,
            "DurationMinutes": self.duration_minutes,
            "Rating": self.rating,
            "Description": self.description
        }


class Theatre:
    def __init__(self, theatre_id, theatre_name, location, total_screens):
        self.theatre_id = theatre_id
        self.theatre_name = theatre_name
        self.location = location
        self.total_screens = total_screens

    def to_dict(self):
        return {
            "TheatreID": self.theatre_id,
            "TheatreName": self.theatre_name,
            "Location": self.location,
            "TotalScreens": self.total_screens
        }


class Screen:
    def __init__(self, screen_id, theatre_id, screen_name, total_seats, seat_layout=None):
        self.screen_id = screen_id
        self.theatre_id = theatre_id
        self.screen_name = screen_name
        self.total_seats = total_seats
        self.seat_layout = seat_layout  # e.g., "Regular: 80, Premium: 20"

    def to_dict(self):
        return {
            "ScreenID": self.screen_id,
            "TheatreID": self.theatre_id,
            "ScreenName": self.screen_name,
            "TotalSeats": self.total_seats,
            "SeatLayout": self.seat_layout
        }


class Show:
    def __init__(self, show_id, movie_id, theatre_id, screen_id, show_date, show_time, ticket_price, total_seats, available_seats, show_status="Active"):
        self.show_id = show_id
        self.movie_id = movie_id
        self.theatre_id = theatre_id
        self.screen_id = screen_id
        self.show_date = show_date
        self.show_time = show_time
        self.ticket_price = ticket_price
        self.total_seats = total_seats
        self.available_seats = available_seats
        self.show_status = show_status

    def to_dict(self):
        return {
            "ShowID": self.show_id,
            "MovieID": self.movie_id,
            "TheatreID": self.theatre_id,
            "ScreenID": self.screen_id,
            "ShowDate": self.show_date,
            "ShowTime": self.show_time,
            "TicketPrice": float(self.ticket_price),
            "TotalSeats": self.total_seats,
            "AvailableSeats": self.available_seats,
            "ShowStatus": self.show_status
        }


class Seat:
    def __init__(self, seat_id, show_id, booking_id, seat_number, seat_category, seat_status="Available"):
        self.seat_id = seat_id
        self.show_id = show_id
        self.booking_id = booking_id
        self.seat_number = seat_number
        self.seat_category = seat_category  # Regular, Premium, Recliner
        self.seat_status = seat_status      # Available, Held, Booked

    def to_dict(self):
        return {
            "SeatID": self.seat_id,
            "ShowID": self.show_id,
            "BookingID": self.booking_id,
            "SeatNumber": self.seat_number,
            "SeatCategory": self.seat_category,
            "SeatStatus": self.seat_status
        }


class Customer:
    def __init__(self, customer_id, full_name, email, phone):
        self.customer_id = customer_id
        self.full_name = full_name
        self.email = email
        self.phone = phone

    def to_dict(self):
        return {
            "CustomerID": self.customer_id,
            "FullName": self.full_name,
            "Email": self.email,
            "Phone": self.phone
        }


class Booking:
    def __init__(self, py_id, customer_id, show_id, number_of_tickets, total_amount, confirmation_flag=0, booking_status="New", payment_status="Pending", booking_reference=None, created_date_time=None):
        self.py_id = py_id
        self.customer_id = customer_id
        self.show_id = show_id
        self.number_of_tickets = number_of_tickets
        self.total_amount = total_amount
        self.confirmation_flag = confirmation_flag
        self.booking_status = booking_status
        self.payment_status = payment_status
        self.booking_reference = booking_reference
        self.created_date_time = created_date_time

    def to_dict(self):
        return {
            "BookingID": self.py_id,
            "CustomerID": self.customer_id,
            "ShowID": self.show_id,
            "NumberOfTickets": self.number_of_tickets,
            "TotalAmount": float(self.total_amount),
            "ConfirmationFlag": bool(self.confirmation_flag),
            "BookingStatus": self.booking_status,
            "PaymentStatus": self.payment_status,
            "BookingReference": self.booking_reference,
            "CreatedDateTime": self.created_date_time
        }


class Notification:
    def __init__(self, notification_id, booking_id, channel, status, sent_date_time):
        self.notification_id = notification_id
        self.booking_id = booking_id
        self.channel = channel
        self.status = status
        self.sent_date_time = sent_date_time

    def to_dict(self):
        return {
            "NotificationID": self.notification_id,
            "BookingID": self.booking_id,
            "Channel": self.channel,
            "Status": self.status,
            "SentDateTime": self.sent_date_time
        }
