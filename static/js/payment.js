function fetchSlots() {
    const date = document.getElementById('date').value;
    if (!date) return;

    fetch(`/api/check_availability?date=${date}`)
        .then(response => response.json())
        .then(bookings => {
            const container = document.getElementById('slots-container');
            container.innerHTML = '';

            // Generate slots from 6 AM to 11 PM
            const slots = [];
            for (let i = 6; i < 23; i++) {
                const hour = i > 12 ? i - 12 : i;
                const ampm = i >= 12 ? 'PM' : 'AM';
                const timeStr = `${hour}:00 ${ampm}`;
                const timeValue = `${i.toString().padStart(2, '0')}:00`;
                slots.push({ display: timeStr, value: timeValue });
            }

            slots.forEach(slot => {
                const btn = document.createElement('div');
                btn.className = 'time-slot';
                btn.textContent = slot.display;

                // Check availability (Mock logic: if entry exists, simplistic check)
                // In real app, check overlap with duration
                const isTaken = bookings.some(b => b.start_time === slot.value + ':00'); // Simple exact match for now

                if (isTaken) {
                    btn.classList.add('booked');
                } else {
                    btn.onclick = () => selectSlot(btn, slot.value);
                }

                container.appendChild(btn);
            });
        });
}

function selectSlot(element, timeValue) {
    document.querySelectorAll('.time-slot').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    document.getElementById('selectedTime').value = timeValue;
    updatePrice();
}

document.getElementById('duration').addEventListener('change', updatePrice);

function updatePrice() {
    const duration = document.getElementById('duration').value;
    const price = duration * 800;
    document.getElementById('total-price').innerText = `₹${price}`;
    document.getElementById('confirm-amount').innerText = price;
}

// --- Payment Timer Logic ---
let paymentTimer;

function startPaymentTimer() {
    // 1. Get Payment Token from Server
    fetch('/api/initiate_payment', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.token) {
                // Set Token
                document.getElementById('payment_token').value = data.token;

                // UI Changes
                document.getElementById('payment-start-section').style.display = 'none';
                document.getElementById('active-payment-section').style.display = 'block';

                // Start Timer
                let timeLeft = 300; // 5 minutes in seconds
                updateTimerDisplay(timeLeft);

                paymentTimer = setInterval(() => {
                    timeLeft--;
                    updateTimerDisplay(timeLeft);

                    if (timeLeft <= 0) {
                        clearInterval(paymentTimer);
                        handlePaymentTimeout();
                    }
                }, 1000);
            }
        })
        .catch(err => {
            alert("Error starting payment session. Please try again.");
            console.error(err);
        });
}

function updateTimerDisplay(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    document.getElementById('time-left').textContent =
        `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function handlePaymentTimeout() {
    alert("Payment time expired! The slot has been released.");
    location.reload(); // Refresh page to reset
}

function validatePayment() {
    // const qrScanned = document.getElementById('qr_scanned').checked; // Removed as element doesn't exist
    const paidAmount = parseFloat(document.getElementById('paid_amount_input').value);
    const requiredAmount = parseFloat(document.getElementById('confirm-amount').innerText);
    const uploadInput = document.getElementById('payment_screenshot');
    const submitBtn = document.getElementById('submitBtn');

    // Warning/Error elements might not exist in new template, check first
    const errorMsg = document.getElementById('payment-error');
    const warningMsg = document.getElementById('upload-warning');

    // Check Amount
    let amountValid = false;
    if (!isNaN(paidAmount) && Math.abs(paidAmount - requiredAmount) < 1) {
        amountValid = true;
        if (errorMsg) errorMsg.style.display = 'none';
    } else {
        if (paidAmount && errorMsg) errorMsg.style.display = 'block';
    }

    // New Logic: If amount is correct, enable file input. If file selected, enable submit.
    if (amountValid) {
        uploadInput.disabled = false;
        if (warningMsg) warningMsg.style.display = 'none';

        if (uploadInput.files.length > 0) {
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
        }
    } else {
        uploadInput.disabled = true;
        submitBtn.disabled = true;
        if (warningMsg) warningMsg.style.display = 'block';
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        // Preview
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.style.maxWidth = '100%';
            img.style.marginTop = '10px';
            document.getElementById('image-preview').innerHTML = '';
            document.getElementById('image-preview').appendChild(img);
        };
        reader.readAsDataURL(file);

        // Re-validate to enable submit button
        validatePayment();
    }
}

function handleBooking(event) {
    event.preventDefault();

    // Final Client Check
    const paidAmount = document.getElementById('paid_amount_input').value;
    const requiredAmount = document.getElementById('confirm-amount').innerText;

    if (paidAmount != requiredAmount) {
        alert("Paid amount must exactly match the total price.");
        return;
    }

    const form = document.getElementById('bookingForm');
    const formData = new FormData(form);
    const submitBtn = document.getElementById('submitBtn');

    submitBtn.disabled = true;
    submitBtn.innerText = "Processing...";

    fetch('/api/book_slot', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                submitBtn.disabled = false;
                submitBtn.innerText = "Register / Confirm Booking";
            } else {
                alert("Booking Confirmed Successfully!");
                window.location.href = '/';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("An error occurred. Please try again.");
            submitBtn.disabled = false;
            submitBtn.innerText = "Register / Confirm Booking";
        });
}
