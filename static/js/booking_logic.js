// booking_logic.js

let allSlots = [];
let bookedIds = [];
let selectedStartId = null;
let selectedEndId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Set min date to today
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.min = new Date().toISOString().split('T')[0];
        // If date is already selected (re-load), load slots
        if (dateInput.value) loadSlots();
    }
});

async function loadSlots() {
    const dateStr = document.getElementById('date').value;
    const container = document.getElementById('slots-container');
    const priceEl = document.getElementById('total-price');
    const confirmAmountEl = document.getElementById('confirm-amount');

    if (!dateStr) return;

    // Reset selection
    selectedStartId = null;
    selectedEndId = null;
    updateBookingInfo();

    container.innerHTML = '<p>Loading slots...</p>';

    try {
        // 1. Fetch Slots (Master Data)
        const slotsRes = await fetch(`/api/slots?date=${dateStr}`);
        if (!slotsRes.ok) {
            const text = await slotsRes.text();
            throw new Error(`Server Error: ${slotsRes.status} ${text}`);
        }
        allSlots = await slotsRes.json();

        // 2. Fetch Booked IDs
        const bookedRes = await fetch(`/api/check_availability?date=${dateStr}`);
        if (!bookedRes.ok) {
            throw new Error(`Availability Error: ${bookedRes.status}`);
        }
        bookedIds = await bookedRes.json();

        renderSlots();

    } catch (err) {
        console.error("Error loading slots:", err);
        container.innerHTML = `<p class="text-danger">Error loading slots: ${err.message}. Please try refreshing.</p>`;
    }
}

function renderSlots() {
    const container = document.getElementById('slots-container');
    const dateStr = document.getElementById('date').value;
    container.innerHTML = '';

    if (allSlots.length === 0) {
        container.innerHTML = '<p>No slots configured.</p>';
        return;
    }

    // Sort slots by start_time just in case
    allSlots.sort((a, b) => a.start_time.localeCompare(b.start_time));

    // Get current time for validation
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const todayYMD = `${year}-${month}-${day}`;
    const isToday = dateStr === todayYMD;

    allSlots.forEach(slot => {
        // Server-side 'is_past' takes precedence, but keep safe default
        let isPast = slot.is_past;

        // Fallback for safety (or if API update hasn't propagated)
        if (isPast === undefined && isToday) {
            const [sHour, sMin] = slot.start_time.split(':');
            const slotDate = new Date();
            slotDate.setHours(sHour, sMin, 0, 0);
            if (slotDate < now) {
                isPast = true;
            }
        }

        const isBooked = bookedIds.includes(slot.id);
        const isUnavailable = isBooked || isPast;

        const el = document.createElement('div');
        el.className = `time-slot ${isUnavailable ? 'booked' : 'available'}`;
        el.textContent = slot.display; // e.g., "10:00 AM"
        el.dataset.id = slot.id;
        el.dataset.time = slot.start_time;

        if (isUnavailable) {
            el.style.backgroundColor = "#ffcccc"; // Light Red
            el.style.color = "#d9534f";
            el.style.cursor = "not-allowed";
            if (isBooked) {
                el.title = "Booked";
            } else {
                el.title = "Time Passed";
                el.style.backgroundColor = "#e0e0e0"; // Grey for past
                el.style.color = "#a0a0a0";
            }
        } else {
            el.style.backgroundColor = "#dff0d8"; // Light Green
            el.style.color = "#3c763d";
            el.onclick = () => handleSlotClick(slot);
        }

        // Highlight Selection (only if available or if we want to show it was selected before? No, reset if invalid usually)
        if (!isUnavailable) {
            if (selectedStartId && selectedEndId) {
                if (isSlotInSelectedRange(slot)) {
                    el.classList.add('selected-range');
                    el.style.backgroundColor = "#4CAF50"; // Darker Green
                    el.style.color = "white";
                }
            } else if (selectedStartId === slot.id) {
                el.classList.add('selected-start');
                el.style.backgroundColor = "#4CAF50";
                el.style.color = "white";
            }
        }

        container.appendChild(el);
    });
}

function handleSlotClick(slot) {
    if (selectedStartId === null) {
        // Select Start
        selectedStartId = slot.id;
        selectedEndId = null; // Reset end
    } else if (selectedStartId === slot.id) {
        // Deselect
        selectedStartId = null;
        selectedEndId = null;
    } else if (selectedEndId === null) {
        // Select End
        // Validate: End must be > Start
        const startSlot = allSlots.find(s => s.id === selectedStartId);

        if (slot.start_time <= startSlot.start_time) {
            // If click is before start, assume new start
            selectedStartId = slot.id;
            selectedEndId = null;
        } else {
            // Check for booked slots in between
            if (isRangeValid(startSlot, slot)) {
                selectedEndId = slot.id;
            } else {
                showCustomAlert("Selection includes booked slots. Please select a continuous available range.", "Invalid Selection", "warning");
            }
        }
    } else {
        // Reset and start new
        selectedStartId = slot.id;
        selectedEndId = null;
    }
    renderSlots();
    updateBookingInfo();
}

function isRangeValid(startSlot, endSlot) {
    // Collect all slots between start and end (inclusive of start, exclusive of end typically, 
    // but here slot selection usually implies "Start of this slot" to "Start of End slot"?
    // User Requirement: "Example: 10:00 AM - 11:00 AM".
    // If I select "10:00" and "11:00", does it mean 1 hour (10-11) or 2 hours (10-11, 11-12)?
    // Usually "Select Time Slot" means chunks.
    // If I click 10:00 AM and 12:00 PM.
    // I interpret this as: Start at 10:00, End at 12:00? (Duration 2h)
    // Or Start Slot 10-11 and End Slot 12-1? (Duration 3h)

    // Given the requirement "Slots are range-based from start to end", 
    // and "Example: 10:00 - 11:00", implies the slots represent the START times.
    // If I select 10:00 (Start) and 12:00 (End), the duration is 12:00 - 10:00 = 2 Hours.
    // The slots covered are 10:00-11:00 AND 11:00-12:00.
    // So the 'End Slot' is effectively the end bound.
    // BUT the active slots in DB are typically 1-hour blocks with start_time.
    // If I click "12:00 PM" as end slot, does it mean include 12-1?
    // Let's assume standard range picker: Click Start, Click End. The range includes the End slot?
    // If I click 10 and 11. Is it 2 hours?
    // Let's assume Inclusive. 10-11 + 11-12.
    // Wait, if I click 10:00 and 11:00. 
    // If 11:00 is 'End Time', then it's 1 hour.
    // If 11:00 is 'End Slot' (inclusive), then it's 2 hours.
    // User said: "When user selects start time and end time: Automatically calculate duration".
    // "Example: 06:00 PM - 07:00 PM".
    // This looks like 1 slot.
    // I will implement Inclusive Logic: Range from Start of StartSlot to End of EndSlot.
    // Each slot has fixed duration 1h (assumed).
    // So 10:00 ID -> 11:00 ID.
    // Range = 10:00 -> 12:00 (2 hours).

    const startIndex = allSlots.findIndex(s => s.id === startSlot.id);
    const endIndex = allSlots.findIndex(s => s.id === endSlot.id);

    // Check all intermediate slots
    for (let i = startIndex; i <= endIndex; i++) {
        const s = allSlots[i];
        if (bookedIds.includes(s.id)) return false;
    }
    return true;
}

function isSlotInSelectedRange(slot) {
    if (!selectedStartId || !selectedEndId) return false;
    const sTime = allSlots.find(s => s.id === selectedStartId).start_time;
    const eTime = allSlots.find(s => s.id === selectedEndId).start_time;
    return slot.start_time >= sTime && slot.start_time <= eTime;
}

function updateBookingInfo() {
    const durationSelect = document.getElementById('duration'); // We might not need this select, but maybe hidden
    const priceEl = document.getElementById('total-price');
    const confirmAmountEl = document.getElementById('confirm-amount');
    const durationDisplay = document.getElementById('duration-display'); // New element

    // Inputs
    const inputStart = document.getElementById('input_start_time');
    const inputEnd = document.getElementById('input_end_time'); // We need End TIME, which is EndSlot Start + 1h

    if (!selectedStartId) {
        priceEl.textContent = "₹0";
        if (confirmAmountEl) confirmAmountEl.textContent = "0";
        if (durationDisplay) durationDisplay.textContent = "0 hours";
        return;
    }

    // If only start selected, default 1 hour
    let startSlot = allSlots.find(s => s.id === selectedStartId);
    let endSlot = selectedEndId ? allSlots.find(s => s.id === selectedEndId) : startSlot;

    // Calculate Duration
    // Time format "HH:MM:SS" or "HH:MM"
    let d1 = new Date(`1970-01-01T${startSlot.start_time}`);
    let d2 = new Date(`1970-01-01T${endSlot.start_time}`);

    // Add 1 hour to d2 (Since End Slot is inclusive, we book UNTIL the end of that slot)
    d2.setHours(d2.getHours() + 1);

    // Diff in hours
    let hours = (d2 - d1) / 3600000;

    // Price Calculation
    let price = hours * 800;

    // Weekend Discount: 100 Rs off for 2 hours on Sat/Sun
    const dateVal = document.getElementById('date').value;
    let day = -1;
    if (dateVal) {
        const parts = dateVal.split('-');
        // Create date object treating the input as local time YYYY-MM-DD
        const checkDate = new Date(parts[0], parts[1] - 1, parts[2]);
        day = checkDate.getDay();
    }

    if ((day === 0 || day === 6) && Math.abs(hours - 2) < 0.01) {
        price = 1500;
        // Optional: Show discount message?
    }

    // UI Update
    priceEl.textContent = `₹${price}`;
    if (confirmAmountEl) confirmAmountEl.textContent = price;
    if (durationDisplay) durationDisplay.textContent = `${hours} hours (${formatTime(d1)} - ${formatTime(d2)})`;

    // Hidden Inputs
    if (inputStart) inputStart.value = toTimeStr(d1);
    if (inputEnd) inputEnd.value = toTimeStr(d2);

    // [NEW] Track Selected IDs and User ID
    let ids = [];
    // Collect IDs in range
    const startIndex = allSlots.findIndex(s => s.id === startSlot.id);
    const endIndex = allSlots.findIndex(s => s.id === endSlot.id);
    for (let i = startIndex; i <= endIndex; i++) {
        ids.push(allSlots[i].id);
    }
    document.getElementById('selected_slot_ids').value = JSON.stringify(ids);

    // Ensure User Identifier
    let uid = localStorage.getItem('user_identifier');
    if (!uid) {
        uid = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('user_identifier', uid);
    }
    document.getElementById('user_identifier').value = uid;
}

function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function toTimeStr(date) {
    return date.toTimeString().split(' ')[0]; // HH:MM:SS
}

// Override Payment.js submit trigger if necessary, or work with it.
// The existing `handleBooking` reads `paid_amount_input`.
// We just need to ensure inputs are populated.
