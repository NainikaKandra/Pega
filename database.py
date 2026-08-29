import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mtbms.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Movie Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Movie (
            MovieID TEXT PRIMARY KEY,
            Title TEXT NOT NULL,
            Genre TEXT,
            Language TEXT,
            DurationMinutes INTEGER,
            Rating TEXT,
            Description TEXT
        )
    """)

    # Create Theatre Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Theatre (
            TheatreID TEXT PRIMARY KEY,
            TheatreName TEXT NOT NULL,
            Location TEXT,
            TotalScreens INTEGER
        )
    """)

    # Create Screen Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Screen (
            ScreenID TEXT PRIMARY KEY,
            TheatreID TEXT,
            ScreenName TEXT NOT NULL,
            TotalSeats INTEGER,
            SeatLayout TEXT,
            FOREIGN KEY (TheatreID) REFERENCES Theatre(TheatreID)
        )
    """)

    # Create Show Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Show (
            ShowID TEXT PRIMARY KEY,
            MovieID TEXT,
            TheatreID TEXT,
            ScreenID TEXT,
            ShowDate TEXT,
            ShowTime TEXT,
            TicketPrice REAL,
            TotalSeats INTEGER,
            AvailableSeats INTEGER,
            ShowStatus TEXT DEFAULT 'Active',
            FOREIGN KEY (MovieID) REFERENCES Movie(MovieID),
            FOREIGN KEY (TheatreID) REFERENCES Theatre(TheatreID),
            FOREIGN KEY (ScreenID) REFERENCES Screen(ScreenID)
        )
    """)

    # Create Seat Table (inventory per show)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Seat (
            SeatID TEXT PRIMARY KEY,
            ShowID TEXT,
            BookingID TEXT,
            SeatNumber TEXT NOT NULL,
            SeatCategory TEXT,
            SeatStatus TEXT DEFAULT 'Available',
            FOREIGN KEY (ShowID) REFERENCES Show(ShowID)
        )
    """)

    # Create Customer Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Customer (
            CustomerID TEXT PRIMARY KEY,
            FullName TEXT NOT NULL,
            Email TEXT NOT NULL,
            Phone TEXT
        )
    """)

    # Create Booking Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Booking (
            pyID TEXT PRIMARY KEY,
            CustomerID TEXT,
            ShowID TEXT,
            NumberOfTickets INTEGER,
            TotalAmount REAL,
            ConfirmationFlag INTEGER DEFAULT 0,
            BookingStatus TEXT DEFAULT 'New',
            PaymentStatus TEXT DEFAULT 'Pending',
            BookingReference TEXT,
            CreatedDateTime TEXT,
            FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID),
            FOREIGN KEY (ShowID) REFERENCES Show(ShowID)
        )
    """)

    # Create Notification Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Notification (
            NotificationID TEXT PRIMARY KEY,
            BookingID TEXT,
            Channel TEXT,
            Status TEXT,
            SentDateTime TEXT,
            FOREIGN KEY (BookingID) REFERENCES Booking(pyID)
        )
    """)

    conn.commit()
    conn.close()

def seed_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM Movie")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Seed Movies
    movies = [
        ("M1", "Dune: Part Two", "Sci-Fi", "English", 166, "PG-13", "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family."),
        ("M2", "Oppenheimer", "Biography / Drama", "English", 180, "R", "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb."),
        ("M3", "Interstellar", "Sci-Fi / Adventure", "English", 169, "PG-13", "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival."),
        ("M4", "Spirited Away", "Animation", "Japanese", 125, "PG", "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits.")
    ]
    cursor.executemany("INSERT INTO Movie VALUES (?, ?, ?, ?, ?, ?, ?)", movies)

    # Seed Theatres
    theatres = [
        ("T1", "CineWave IMAX Downtown", "New York, NY", 2),
        ("T2", "CineWave Galleria", "Los Angeles, CA", 2)
    ]
    cursor.executemany("INSERT INTO Theatre VALUES (?, ?, ?, ?)", theatres)

    # Seed Screens
    screens = [
        ("S1", "T1", "IMAX Screen 1", 30, "A1-A10 (Regular), B1-B10 (Premium), C1-C10 (Recliner)"),
        ("S2", "T1", "Screen 2", 20, "A1-A10 (Regular), B1-B10 (Premium)"),
        ("S3", "T2", "Grand Screen 1", 30, "A1-A10 (Regular), B1-B10 (Premium), C1-C10 (Recliner)"),
        ("S4", "T2", "Screen 2", 20, "A1-A10 (Regular), B1-B10 (Premium)")
    ]
    cursor.executemany("INSERT INTO Screen VALUES (?, ?, ?, ?, ?)", screens)

    # Seed Shows (let's create a few shows)
    import datetime
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    day_after = today + datetime.timedelta(days=2)

    shows = [
        ("SH1", "M1", "T1", "S1", tomorrow.strftime("%Y-%m-%d"), "18:00", 15.50, 30, 30, "Active"),
        ("SH2", "M1", "T1", "S1", tomorrow.strftime("%Y-%m-%d"), "21:15", 15.50, 30, 30, "Active"),
        ("SH3", "M2", "T1", "S2", tomorrow.strftime("%Y-%m-%d"), "14:00", 12.00, 20, 20, "Active"),
        ("SH4", "M3", "T2", "S3", tomorrow.strftime("%Y-%m-%d"), "19:00", 14.00, 30, 30, "Active"),
        ("SH5", "M4", "T2", "S4", day_after.strftime("%Y-%m-%d"), "11:00", 10.00, 20, 20, "Active")
    ]
    cursor.executemany("INSERT INTO Show VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", shows)

    # Seed Seats for each Show
    # For S1/S3: 3 rows (A, B, C) x 10 = 30 seats
    # For S2/S4: 2 rows (A, B) x 10 = 20 seats
    seat_records = []
    for show in shows:
        show_id = show[0]
        screen_id = show[3]
        
        num_rows = 3 if screen_id in ("S1", "S3") else 2
        for r_idx, row_char in enumerate(["A", "B", "C"][:num_rows]):
            # Assign category
            if row_char == "A":
                cat = "Regular"
            elif row_char == "B":
                cat = "Premium"
            else:
                cat = "Recliner"
                
            for col in range(1, 11):
                seat_num = f"{row_char}{col}"
                seat_id = f"{show_id}_{seat_num}"
                seat_records.append((seat_id, show_id, None, seat_num, cat, "Available"))
                
    cursor.executemany("INSERT INTO Seat VALUES (?, ?, ?, ?, ?, ?)", seat_records)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    print("Database initialized and seeded.")
