document.addEventListener("DOMContentLoaded", function () {
    const seatContainer = document.querySelector(".seat-map-grid");
    if (!seatContainer) return;

    const ticketCount = parseInt(seatContainer.getAttribute("data-ticket-count"), 10);
    const selectedSeatsInput = document.getElementById("selected-seats-input");
    const submitBtn = document.getElementById("submit-seats-btn");
    const selectionCountEl = document.getElementById("selection-count");

    let selectedSeats = [];

    // Select all seat elements that are available
    const seats = document.querySelectorAll(".seat.available-Regular, .seat.available-Premium, .seat.available-Recliner");

    seats.forEach(seat => {
        seat.addEventListener("click", function () {
            const seatNum = this.getAttribute("data-seat-number");

            if (this.classList.contains("selected")) {
                // Deselect
                this.classList.remove("selected");
                selectedSeats = selectedSeats.filter(s => s !== seatNum);
            } else {
                // Select if limit not reached
                if (selectedSeats.length < ticketCount) {
                    this.classList.add("selected");
                    selectedSeats.push(seatNum);
                } else {
                    alert(`You can only select up to ${ticketCount} seat(s). Deselect a seat first to change your selection.`);
                }
            }

            updateSelectionState();
        });
    });

    function updateSelectionState() {
        // Update hidden inputs in the form
        // Clear previous hidden fields
        const existingInputs = document.querySelectorAll(".hidden-seat-field");
        existingInputs.forEach(el => el.remove());

        selectedSeats.forEach(seatNum => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "seats";
            input.value = seatNum;
            input.className = "hidden-seat-field";
            selectedSeatsInput.appendChild(input);
        });

        // Update counts and button state
        selectionCountEl.textContent = selectedSeats.length;

        if (selectedSeats.length === ticketCount) {
            submitBtn.removeAttribute("disabled");
            submitBtn.classList.remove("btn-secondary");
            submitBtn.classList.add("btn-primary");
        } else {
            submitBtn.setAttribute("disabled", "true");
            submitBtn.classList.remove("btn-primary");
            submitBtn.classList.add("btn-secondary");
        }
    }
});
