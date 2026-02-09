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

async function startPaymentTimer() {
    const slotIdsStr = document.getElementById('selected_slot_ids').value;
    const uid = document.getElementById('user_identifier').value;

    if (!slotIdsStr || !uid) {
        showCustomAlert("Please select slots first.", "Error", "error");
        return;
    }
    const slotIds = JSON.parse(slotIdsStr);

    // 0. Try Lock
    try {
        for (let sid of slotIds) {
            const res = await fetch('/api/lock_slot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ slot_id: sid, user_identifier: uid })
            });
            const data = await res.json();
            if (!res.ok) {
                showCustomAlert(data.error || "Slot unavailable", "Lock Failed", "error");
                // Optional: Refresh slots
                if (typeof loadSlots === 'function') loadSlots();
                return;
            }
        }
    } catch (e) {
        console.error(e);
        showCustomAlert("Network error locking slots", "Error", "error");
        return;
    }

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
            console.error("Error starting payment session:", err);
        });
}

function updateTimerDisplay(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    document.getElementById('time-left').textContent =
        `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function handlePaymentTimeout() {
    showCustomAlert("Payment time expired! The slot has been released.", "Timeout", "error");
    setTimeout(() => location.reload(), 2000); // Wait for user to read
}

function validatePayment() {
    const uploadInput = document.getElementById('payment_screenshot');
    const submitBtn = document.getElementById('submitBtn');
    const warningMsg = document.getElementById('upload-warning');

    // Validation: Only check if file is selected
    if (uploadInput.files.length > 0) {
        submitBtn.disabled = false;
        if (warningMsg) warningMsg.style.display = 'none';
    } else {
        submitBtn.disabled = true;
        if (warningMsg) warningMsg.style.display = 'block';
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    const fileNameDisplay = document.getElementById('file-name-display');
    const errorMsg = document.getElementById('upload-error');
    const previewContainer = document.getElementById('image-preview');
    const submitBtn = document.getElementById('submitBtn');

    // Reset
    previewContainer.innerHTML = '';
    errorMsg.style.display = 'none';
    errorMsg.textContent = '';
    submitBtn.disabled = true;

    if (!file) {
        fileNameDisplay.textContent = "No file chosen";
        return;
    }

    // 1. Validate File Type (MIME)
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        errorMsg.textContent = "Error: Only PNG and JPEG images are allowed.";
        errorMsg.style.display = 'block';
        event.target.value = ''; // Clear input
        fileNameDisplay.textContent = "No file chosen";
        return;
    }

    // 2. Validate Size (Max 2MB)
    const maxSize = 2 * 1024 * 1024; // 2MB
    if (file.size > maxSize) {
        errorMsg.textContent = "Error: Image size exceeds 2MB limit.";
        errorMsg.style.display = 'block';
        event.target.value = ''; // Clear input
        fileNameDisplay.textContent = "No file chosen";
        return;
    }

    // Valid
    fileNameDisplay.textContent = file.name;

    // Preview
    const reader = new FileReader();
    reader.onload = function (e) {
        const img = document.createElement('img');
        img.src = e.target.result;
        img.style.maxWidth = '100%';
        img.style.maxHeight = '300px';
        img.style.border = '1px solid #ddd';
        img.style.borderRadius = '4px';
        img.style.marginTop = '10px';
        previewContainer.appendChild(img);
    };
    reader.readAsDataURL(file);

    // Re-validate to enable submit button
    validatePayment();
}

function handleBooking(event) {
    event.preventDefault();

    // Final Client Check
    // Removed paidAmount check as it's no longer input by user

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
                showCustomAlert(data.error, "Booking Failed", "error");
                submitBtn.disabled = false;
                submitBtn.innerText = "Register / Confirm Booking";
            } else {
                showCustomAlert("Booking Confirmed Successfully!", "Success", "success");
                setTimeout(() => window.location.href = '/', 2000);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showCustomAlert("An error occurred. Please try again.", "Error", "error");
            submitBtn.disabled = false;
            submitBtn.innerText = "Register / Confirm Booking";
        });
}
