frontend.js


// 1. Wait for the page to load before we start looking for buttons
document.addEventListener('DOMContentLoaded', () => {
    const searchButton = document.getElementById('search-btn');
    
    // 2. Listen for the click
    searchButton.addEventListener('click', () => {
        performSearch();
    });
});

async function performSearch() {
    // 3. Get values from your HTML inputs
    const query = document.getElementById('search-input').value;
    const onlyAnnotated = document.getElementById('annotated-checkbox').checked;

    // 4. Talk to the Backend (FastAPI)
    try {
        const response = await fetch(`/search?q=${query}&annotated=${onlyAnnotated}`);
        const data = await response.json(); // Convert the answer to a JS object

        // 5. Send the data to a function to show it on the screen
        displayResults(data);
    } catch (error) {
        console.error("Search failed:", error);
    }
}


function displayResults(data) {
    const container = document.getElementById('results-container');
    container.innerHTML = ''; // Clear previous results

    if (data.length === 0) {
        container.innerHTML = '<p>No matching arguments found.</p>';
        return;
    }

    data.forEach(item => {
        // Create a 'card' for each Reddit thread
        const card = document.createElement('div');
        card.className = 'result-card';
        
        // Add a "Badge" based on the Success Score (0, 1, 2)
        const scoreClass = getScoreClass(item.success_score);
        
        card.innerHTML = `
            <h3>Thread #${item.doc_id}</h3>
            <p>${item.summary_text.substring(0, 100)}...</p>
            <span class="badge ${scoreClass}">Success: ${item.success_score}</span>
        `;

        // When clicked, show the full details in the main pane
        card.addEventListener('click', () => showDetailedView(item));
        
        container.appendChild(card);
    });
}



// this funtion ensures the labels are in css classes so we can color them

function getScoreClass(score) {
    if (score === 2) return 'score-high';   // Green
    if (score === 1) return 'score-medium'; // Yellow
    return 'score-low';                     // Red
}


// this function adds visual elements when clicking on labels

function showDetailedView(item) {
    const detailPane = document.getElementById('detail-pane');
    
    detailPane.innerHTML = `
        <div class="detail-header">
            <h2>Detailed Audit: Document ${item.doc_id}</h2>
            <div class="metrics-row">
                <span class="badge ${getScoreClass(item.success_score)}">Success: ${item.success_score}</span>
                <span class="badge ${getScoreClass(item.brevity_score)}">Brevity: ${item.brevity_score}</span>
                <span class="badge ${getScoreClass(item.accuracy_score)}">Accuracy: ${item.accuracy_score}</span>
            </div>
        </div>
        
        <div class="content-split">
            <div class="source-box">
                <h3>Original Reddit Argument</h3>
                <p>${item.source_text}</p>
            </div>
            <div class="summary-box">
                <h3>Model-Generated Summary</h3>
                <p>${item.summary_text}</p>
            </div>
        </div>
    `;
}

