// Polling interval in milliseconds
const POLL_INTERVAL = 500;

document.addEventListener("DOMContentLoaded", () => {
    // Start the continuous loop to fetch coordinates without reloading
    setInterval(fetchLiveCoordinates, POLL_INTERVAL);

    // Initial fetch to populate immediately
    fetchLiveCoordinates();
});

/**
 * Fetch the latest JSON data for both known and unknown entities
 */
async function fetchLiveCoordinates() {
    try {
        const [knownRes, unknownRes] = await Promise.all([
            fetch('/faces').catch(() => null),
            fetch('/unknowns').catch(() => null)
        ]);

        if (knownRes && knownRes.ok) {
            const data = await knownRes.json();
            // Data might come as { timestamp, faces } or { timestamp, known_faces }
            const knownPeople = data.known_faces || data.faces || [];
            updateCards('known-list', knownPeople, 'known');
        }

        if (unknownRes && unknownRes.ok) {
            const data = await unknownRes.json();
            const unknownPeople = data.unknown_faces || data.unknowns || [];
            updateCards('unknown-list', unknownPeople, 'unknown');
        }
    } catch (error) {
        console.error("Error fetching live coordinates:", error);
    }
}

/**
 * Update the UI grid smoothly tracking person IDs to prevent jittering/flickering
 */
function updateCards(containerId, people, type) {
    const container = document.getElementById(containerId);

    // Show empty state if no one is detected
    if (!people || people.length === 0) {
        container.innerHTML = `<p class="empty-state">Waiting for detections...</p>`;
        return;
    }

    // Clear empty state message if it is currently displayed
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    // Collect all incoming IDs for this category
    const incomingIds = new Set(people.map(p => p.id));

    // 1. Remove cards for IDs that are no longer detected
    Array.from(container.children).forEach(child => {
        if (!child.dataset) return; // Ignore non-card elements if any
        const cardId = parseInt(child.dataset.id, 10);
        if (!incomingIds.has(cardId)) {
            // Add a fade out animation here if desired, then remove
            child.remove();
        }
    });

    // 2. Add or update existing cards
    people.forEach(person => {
        let card = container.querySelector(`.person-card[data-id="${person.id}"]`);

        // Formulate image URL based on whether python saved an image or not
        const imageUrl = person.image_file
            ? `/face-image/${encodeURIComponent(person.image_file)}`
            : `https://ui-avatars.com/api/?name=${encodeURIComponent(person.name)}&background=1e293b&color=fff&size=128`;

        if (!card) {
            // Card doesn't exist yet, build new HTML
            card = document.createElement('div');
            card.className = `person-card ${type}`;
            card.dataset.id = person.id;

            card.innerHTML = `
                <div class="card-image-wrap">
                    <img class="person-img" src="${imageUrl}" alt="${person.name}">
                    <div class="pulse-ring"></div>
                </div>
                <div class="card-info">
                    <h3 class="person-name">${person.name}</h3>
                    <div class="person-meta">Track ID: <span>#${person.id}</span></div>
                    <div class="coordinates">
                        <div class="coord-item">
                            <span class="coord-label">X</span>
                            <span class="coord-value x-val">${person.coordinates.center_x}</span>
                        </div>
                        <div class="coord-item">
                            <span class="coord-label">Y</span>
                            <span class="coord-value y-val">${person.coordinates.center_y}</span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(card);
        } else {
            // Simply update the card info if it already exists to avoid DOM recreation
            // Only swap image src if it has fundamentally changed entirely (otherwise browser might flicker on identical URL assignment)
            const imgEl = card.querySelector('.person-img');
            const newSrcPath = new URL(imageUrl, window.location.origin).pathname;
            const currentSrcPath = new URL(imgEl.src, window.location.origin).pathname;

            if (currentSrcPath !== newSrcPath) {
                imgEl.src = imageUrl;
            }

            card.querySelector('.person-name').textContent = person.name;
            card.querySelector('.x-val').textContent = person.coordinates.center_x;
            card.querySelector('.y-val').textContent = person.coordinates.center_y;
        }
    });
}
