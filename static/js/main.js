document.addEventListener('DOMContentLoaded', () => {
    // If on tournaments page, load tournaments
    if (document.getElementById('tournament-list')) {
        loadTournaments();
    }
});

// --- Tournament Logic ---

async function loadTournaments() {
    const listContainer = document.getElementById('tournament-list');

    try {
        const response = await fetch('/api/tournaments');
        const tournaments = await response.json();

        listContainer.innerHTML = '';

        if (tournaments.length === 0) {
            listContainer.innerHTML = '<p>No upcoming tournaments.</p>';
            return;
        }

        tournaments.forEach(t => {
            const card = document.createElement('div');
            card.className = 'tournament-card';
            // Format date
            const date = new Date(t.event_date).toLocaleDateString();

            // Construct image path - use local static path for uploaded images
            let imageSrc = '/static/tournament_images/default.jpg';
            // The DB column is 'image_url', make sure API returns it (SELECT * returns it)
            // Backend keys match DB columns usually in simple SELECT *
            let imgVal = t.image_url || t.image; // Fallback just in case

            if (imgVal) {
                // Check if it's a full URL or just a filename
                if (imgVal.startsWith('http')) {
                    imageSrc = imgVal;
                } else {
                    imageSrc = `/static/tournament_images/${imgVal}`;
                }
            }

            card.innerHTML = `
                <div class="t-image">
                    <img src="${imageSrc}" alt="${t.title}" onerror="this.src='/static/tournament_images/default.jpg'">
                </div>
                <div class="t-info">
                    <h3>${t.title}</h3>
                    <p>${t.description}</p>
                    <div class="t-details">
                        <span><i class="far fa-calendar"></i> ${date}</span>
                        <span><i class="fas fa-money-bill"></i> ₹${t.entry_fee}</span>
                    </div>
                </div>
            `;
            // Register Button
            card.innerHTML += `<div style="padding:15px;"><button class="btn-cta" onclick="openRegModal('${t.id}')">Register Team</button></div>`;

            listContainer.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading tournaments:', error);
        listContainer.innerHTML = '<p>Error loading tournaments.</p>';
    }
}

// --- Modal Logic ---
const modal = document.getElementById('regModal');

// Ensure modal exists before adding listeners
if (modal) {
    window.onclick = function (event) {
        if (event.target == modal) {
            closeModal();
        }
    }
}

function openRegModal(tournamentId) {
    const tInput = document.getElementById('tournamentId');
    if (tInput && modal) {
        tInput.value = tournamentId;
        modal.style.display = 'block';
    } else {
        showCustomAlert('Registration unavailable at the moment.', 'Info');
    }
}

function closeModal() {
    if (modal) {
        modal.style.display = 'none';
    }
}


async function handleRegistration(event) {
    event.preventDefault();
    const formData = {
        tournament_id: document.getElementById('tournamentId').value,
        team_name: document.getElementById('teamName').value,
        captain_name: document.getElementById('captainName').value,
        captain_phone: document.getElementById('captainPhone').value
    };

    try {
        const response = await fetch('/api/register_tournament', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (response.ok) {
            showCustomAlert('Registration Successful!', 'Success');
            closeModal();
            loadTournaments(); // Refresh list if needed (e.g. to update counts)
        } else {
            showCustomAlert(result.error || 'Registration failed', 'Error');
        }
    } catch (error) {
        showCustomAlert('Registration failed. Please try again.', 'Error');
    }
}
