# CineWave Entertainment — Movie Ticket Booking Case Simulator
### Pega App Studio Case Lifecycle Simulator (Flask + SQLite)

This application is a build-ready simulation of the **CineWave Movie Ticket Booking Management System (MTBMS)** designed in accordance with the Pega Platform App Studio specifications. It simulates case workflows, state transitions, validation rules, decision models, background SLAs, and automated notification triggers.

---

## 🔗 Live Public Demo Link
Access the running application online from any device:
👉 **[https://fixtures-tiles-cheese-horn.trycloudflare.com](https://fixtures-tiles-cheese-horn.trycloudflare.com)**

*(Note: The demo link is actively served via a secure tunnel from the local development server).*

---

## ⚙️ Core Simulated Pega Features

### 1. Case Lifecycle Stepper (stages & statuses)
Tracks case transitions through five stages with standard work status codes:
1. **Booking Request** (`New`)
2. **Availability Check** (`Pending-Availability`)
3. **Customer Confirmation** (`Pending-Confirmation`)
4. **Booking Processing** (`Open-InProgress`)
5. **Confirmed & Notified** (`Resolved-Completed`)

*Includes alternate paths for exceptions: `Resolved-NoAvailability`, `Resolved-Declined`, and `Resolved-PaymentFailed`.*

### 2. Business Validation & Decision Rules
- **Validate Form Rules**: Ensures email formatting, mandatory fields, and ticket count boundaries are met.
- **IsShowValid / IsSeatAvailable**: Checks capacity and date validations before booking tickets.

### 3. SLA Hold Escalation (30-Minute Timer)
Simulates Pega's SLA hold duration. When a seat selection is held (Stage 3), a background daemon thread monitors the transaction time. If 30 minutes pass without confirmation:
1. The case transitions to `Resolved-NoAvailability`.
2. Held seats are released back to public availability.
3. An automated cancellation notification is dispatched.

---

## 🛠️ Local Setup and Run

### Prerequisites
- Python 3.11+
- Flask (`pip install flask`)
- Websocket Client (`pip install websocket-client` - optional, for devtools)

### 1. Initialize & Seed Database
Create the SQLite schema and seed mock movies, screens, shows, and grids:
```bash
python3 database.py
```

### 2. Run Flask Web Application
Start the server locally:
```bash
python3 app.py
```
Open **[http://127.0.0.1:5001](http://127.0.0.1:5001)** in your browser.

---

## 🧪 Running Automated Tests
The application includes a comprehensive test suite covering the happy path, alternate paths, and SLA timeouts:
```bash
python3 -m unittest tests/test_booking.py
```
