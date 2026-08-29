import unittest
import os
import sqlite3
import datetime
import database
import app as flask_app
from database import init_db, seed_db

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "test_mtbms.db")

class BookingLifecycleTestCase(unittest.TestCase):

    def setUp(self):
        # Override database path to use a test database
        database.DB_PATH = TEST_DB_PATH
        flask_app.DB_PATH = TEST_DB_PATH
        
        # Clean test DB
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
            
        init_db()
        seed_db()
        
        # Configure app for testing
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["WTF_CSRF_ENABLED"] = False
        self.client = flask_app.app.test_client()

    def tearDown(self):
        # Clean up test DB
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_happy_path_booking_completed(self):
        # 1. Start Stage 1 Booking Request
        response = self.client.post("/booking/new", data={
            "movie_id": "M1",
            "theatre_id": "T1",
            "show_id": "SH1",
            "ticket_count": "2",
            "full_name": "Test Customer",
            "email": "test@cinewave.com",
            "phone": "+1999999999"
        }, follow_redirects=False)
        
        # Should redirect to Stage 2: Seat Selection
        self.assertEqual(response.status_code, 302)
        booking_url = response.location
        booking_id = booking_url.split("/")[-2] # e.g. /booking/<id>/select-seats -> id
        
        # Verify Booking case exists in DB with status 'New'
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM Booking WHERE pyID = ?", (booking_id,))
        booking = cur.fetchone()
        self.assertIsNotNone(booking)
        self.assertEqual(booking["BookingStatus"], "New")
        self.assertEqual(booking["NumberOfTickets"], 2)
        
        # 2. Stage 2: Select Seats (A1, A2)
        response = self.client.post(f"/booking/{booking_id}/select-seats", data={
            "seats": ["A1", "A2"]
        }, follow_redirects=False)
        
        # Should redirect to Stage 3: Confirm
        self.assertEqual(response.status_code, 302)
        self.assertIn("confirm", response.location)
        
        # Verify seats status updated to 'Held' in DB and BookingStatus to 'Pending-Confirmation'
        cur.execute("SELECT SeatStatus FROM Seat WHERE BookingID = ?", (booking_id,))
        seats = cur.fetchall()
        self.assertEqual(len(seats), 2)
        for s in seats:
            self.assertEqual(s["SeatStatus"], "Held")
            
        cur.execute("SELECT BookingStatus FROM Booking WHERE pyID = ?", (booking_id,))
        self.assertEqual(cur.fetchone()["BookingStatus"], "Pending-Confirmation")

        # 3. Stage 3: Customer Confirmation (Confirm)
        response = self.client.post(f"/booking/{booking_id}/confirm", data={
            "action": "confirm"
        }, follow_redirects=False)
        
        # Should redirect to Stage 4: Process
        self.assertEqual(response.status_code, 302)
        self.assertIn("process", response.location)
        
        # Verify ConfirmationFlag is set and status is 'Open-InProgress'
        cur.execute("SELECT ConfirmationFlag, BookingStatus FROM Booking WHERE pyID = ?", (booking_id,))
        row = cur.fetchone()
        self.assertEqual(row["ConfirmationFlag"], 1)
        self.assertEqual(row["BookingStatus"], "Open-InProgress")

        # 4. Stage 4: Booking Processing (Simulate Payment Success)
        response = self.client.post(f"/booking/{booking_id}/process", data={
            "payment_status": "success"
        }, follow_redirects=False)
        
        # Should redirect to Stage 5: Final
        self.assertEqual(response.status_code, 302)
        self.assertIn("final", response.location)
        
        # Verify final status 'Resolved-Completed', payment 'Paid', reference generated, and inventory updated
        cur.execute("SELECT BookingStatus, PaymentStatus, BookingReference FROM Booking WHERE pyID = ?", (booking_id,))
        row = cur.fetchone()
        self.assertEqual(row["BookingStatus"], "Resolved-Completed")
        self.assertEqual(row["PaymentStatus"], "Paid")
        self.assertIsNotNone(row["BookingReference"])
        self.assertTrue(row["BookingReference"].startswith("CW-SH1-"))
        
        # Verify seats status updated to 'Booked'
        cur.execute("SELECT SeatStatus FROM Seat WHERE BookingID = ?", (booking_id,))
        seats = cur.fetchall()
        self.assertEqual(len(seats), 2)
        for s in seats:
            self.assertEqual(s["SeatStatus"], "Booked")
            
        # Verify show available seats decremented from 30 to 28
        cur.execute("SELECT AvailableSeats FROM Show WHERE ShowID = 'SH1'")
        self.assertEqual(cur.fetchone()["AvailableSeats"], 28)
        
        # Verify notification created
        cur.execute("SELECT COUNT(*) FROM Notification WHERE BookingID = ?", (booking_id,))
        self.assertTrue(cur.fetchone()[0] > 0)
        
        conn.close()

    def test_alternate_path_decline(self):
        # 1. Start Stage 1 Booking Request
        response = self.client.post("/booking/new", data={
            "movie_id": "M1",
            "theatre_id": "T1",
            "show_id": "SH1",
            "ticket_count": "1",
            "full_name": "Decliner Customer",
            "email": "decline@cinewave.com",
            "phone": ""
        }, follow_redirects=False)
        booking_id = response.location.split("/")[-2]
        
        # 2. Stage 2: Select Seat (B1)
        self.client.post(f"/booking/{booking_id}/select-seats", data={"seats": ["B1"]}, follow_redirects=False)
        
        # 3. Stage 3: Decline Confirmation
        response = self.client.post(f"/booking/{booking_id}/confirm", data={
            "action": "decline"
        }, follow_redirects=False)
        
        # Should redirect to final resolution summary
        self.assertEqual(response.status_code, 302)
        self.assertIn("final", response.location)
        
        # Verify BookingStatus is 'Resolved-Declined' and seat released
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT BookingStatus FROM Booking WHERE pyID = ?", (booking_id,))
        self.assertEqual(cur.fetchone()["BookingStatus"], "Resolved-Declined")
        
        # Verify seat B1 reverted to 'Available' and clear BookingID
        cur.execute("SELECT SeatStatus, BookingID FROM Seat WHERE ShowID = 'SH1' AND SeatNumber = 'B1'")
        row = cur.fetchone()
        self.assertEqual(row["SeatStatus"], "Available")
        self.assertIsNone(row["BookingID"])
        conn.close()

    def test_alternate_path_no_availability(self):
        # 1. Request more seats than show capacity (capacity is 30)
        response = self.client.post("/booking/new", data={
            "movie_id": "M1",
            "theatre_id": "T1",
            "show_id": "SH1",
            "ticket_count": "40", # capacity is 30
            "full_name": "Overbook Customer",
            "email": "overbook@cinewave.com",
            "phone": ""
        }, follow_redirects=False)
        booking_id = response.location.split("/")[-2]
        
        # 2. Load Select Seats page - should check IsSeatAvailable and fail/redirect to final
        response = self.client.get(f"/booking/{booking_id}/select-seats", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("final", response.location)
        
        # Verify BookingStatus is 'Resolved-NoAvailability'
        conn = sqlite3.connect(TEST_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT BookingStatus FROM Booking WHERE pyID = ?", (booking_id,))
        self.assertEqual(cur.fetchone()[0], "Resolved-NoAvailability")
        conn.close()

    def test_alternate_path_payment_failed(self):
        # 1. Start Booking Request
        response = self.client.post("/booking/new", data={
            "movie_id": "M1",
            "theatre_id": "T1",
            "show_id": "SH1",
            "ticket_count": "1",
            "full_name": "FailedPay Customer",
            "email": "fail@cinewave.com",
            "phone": ""
        }, follow_redirects=False)
        booking_id = response.location.split("/")[-2]
        
        # 2. Select Seat (C1)
        self.client.post(f"/booking/{booking_id}/select-seats", data={"seats": ["C1"]}, follow_redirects=False)
        
        # 3. Confirm Details
        self.client.post(f"/booking/{booking_id}/confirm", data={"action": "confirm"}, follow_redirects=False)
        
        # 4. Process Payment (Fail)
        response = self.client.post(f"/booking/{booking_id}/process", data={
            "payment_status": "failure"
        }, follow_redirects=False)
        
        # Should redirect to final resolution summary
        self.assertEqual(response.status_code, 302)
        self.assertIn("final", response.location)
        
        # Verify BookingStatus is 'Resolved-PaymentFailed' and seat C1 released
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT BookingStatus, PaymentStatus FROM Booking WHERE pyID = ?", (booking_id,))
        row = cur.fetchone()
        self.assertEqual(row["BookingStatus"], "Resolved-PaymentFailed")
        self.assertEqual(row["PaymentStatus"], "Failed")
        
        # Verify seat C1 reverted to 'Available'
        cur.execute("SELECT SeatStatus FROM Seat WHERE ShowID = 'SH1' AND SeatNumber = 'C1'")
        self.assertEqual(cur.fetchone()["SeatStatus"], "Available")
        conn.close()

    def test_sla_expiry(self):
        # 1. Start Booking Request
        response = self.client.post("/booking/new", data={
            "movie_id": "M1",
            "theatre_id": "T1",
            "show_id": "SH1",
            "ticket_count": "1",
            "full_name": "SLA Expire Customer",
            "email": "sla@cinewave.com",
            "phone": ""
        }, follow_redirects=False)
        booking_id = response.location.split("/")[-2]
        
        # 2. Select Seat (C2)
        self.client.post(f"/booking/{booking_id}/select-seats", data={"seats": ["C2"]}, follow_redirects=False)
        
        # Verify seat is Held in DB
        conn = sqlite3.connect(TEST_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT SeatStatus FROM Seat WHERE ShowID = 'SH1' AND SeatNumber = 'C2'")
        self.assertEqual(cur.fetchone()[0], "Held")
        conn.close()
        
        # 3. Trigger manual SLA expiry (post request to dashboard expiry route)
        response = self.client.post(f"/dashboard/expire/{booking_id}", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        
        # Verify case resolved to Resolved-NoAvailability and seat released
        conn = sqlite3.connect(TEST_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT BookingStatus FROM Booking WHERE pyID = ?", (booking_id,))
        self.assertEqual(cur.fetchone()[0], "Resolved-NoAvailability")
        
        cur.execute("SELECT SeatStatus FROM Seat WHERE ShowID = 'SH1' AND SeatNumber = 'C2'")
        self.assertEqual(cur.fetchone()[0], "Available")
        conn.close()

if __name__ == "__main__":
    unittest.main()
