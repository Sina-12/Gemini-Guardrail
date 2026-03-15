// ── State ──────────────────────────────────────────────────────────────────────
// Store all thread data after loading and keep track of the thread the user opened
let allThreads   = [];
let activeThread = null;

// ── Boot ───────────────────────────────────────────────────────────────────────
/**
 * Set up the page once the HTML is fully loaded.
 *
 * This loads the initial data from the back end and connects the search box
 * and search button to the filtering logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    loadAllThreads();

    document.getElementById('search-input').addEventListener('input', debounce(filterThreads, 220));
    document.getElementById('search-btn').addEventListener('click', filterThreads);
    document.getElementById('search-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') filterThreads();
    });
});

// ── Data loading ───────────────────────────────────────────────────────────────
/**
 * Load all thread data from the back end when the page first opens.
 *
 * This gives the app the full set of threads so the list can be shown right away.
 * If the request fails, an error message is shown in the results area.
 */
async function loadAllThreads() {
    setResultsLoading(true);
    try {
        const res = await fetch('/threads');
        allThreads = await res.json();
        renderThreadList(allThreads);
    } catch (err) {
        showResultsError('Could not connect to backend. Is uvicorn running?');
    } finally {
        setResultsLoading(false);
    }
}

// ── Search / filter ────────────────────────────────────────────────────────────
/**
 * Filter threads based on the user's search query.
 *
 * If the search box is empty, this reloads all threads. Otherwise it sends
 * the keyword to the back end and shows only matching results.
 */
async function filterThreads() {
    const q = document.getElementById('search-input').value.trim();
    setResultsLoading(true);
    try {
        const url = q ? `/threads?q=${encodeURIComponent(q)}` : '/threads';
        const res = await fetch(url);
        const threads = await res.json();
        renderThreadList(threads);
        document.getElementById('result-count').textContent =
            `${threads.length} thread${threads.length !== 1 ? 's' : ''}`;
    } catch (err) {
        showResultsError('Search failed.');
    } finally {
        setResultsLoading(false);
    }
}

// ── Render thread list ─────────────────────────────────────────────────────────
/**
 * Render the list of thread cards in the left panel.
 *
 * Each card shows the thread number, small status pills, and a short snippet.
 * Clicking a card opens the full detail view on the right side.
 */
function renderThreadList(threads) {
    const container = document.getElementById('results-container');
    document.getElementById('result-count').textContent =
        `${threads.length} thread${threads.length !== 1 ? 's' : ''}`;

    if (threads.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">∅</div>
                <p>No threads match your search.</p>
            </div>`;
        return;
    }

    container.innerHTML = '';
    threads.forEach(thread => {
        const card = document.createElement('div');
        card.className = 'thread-card';
        if (thread.thread_num === activeThread) card.classList.add('active');
        card.dataset.threadNum = thread.thread_num;

        // Use the original branch text first for the snippet, then fall back to the summary
        const anchor = thread.s || thread.u;
        const snippetSource = anchor?.source_text || anchor?.summary || '—';
        const snippet = snippetSource.substring(0, 90).replace(/\n/g, ' ') + '…';

        const sBadge = thread.s ? scorePill('S', thread.s) : '<span class="pill pill-missing">S —</span>';
        const uBadge = thread.u ? scorePill('U', thread.u) : '<span class="pill pill-missing">U —</span>';

        card.innerHTML = `
            <div class="thread-card-header">
                <span class="thread-id">Thread #${thread.thread_num}</span>
                <div class="thread-pills">${sBadge}${uBadge}</div>
            </div>
            <p class="thread-snippet">${snippet}</p>
        `;

        card.addEventListener('click', () => openThread(thread));
        container.appendChild(card);
    });
}

/**
 * Build a small score pill for the thread list.
 *
 * This gives a quick visual cue for whether the sentiment label was correct
 * for the successful or unsuccessful side.
 */
function scorePill(label, variant) {
    const sentClass = variant.sentiment === 1 ? 'good' : 'bad';
    return `<span class="pill pill-${label.toLowerCase()} pill-sent-${sentClass}" title="Sentiment:${variant.sentiment} Accuracy:${variant.accuracy} Brevity:${variant.brevity}">${label}</span>`;
}

// ── Open thread detail ─────────────────────────────────────────────────────────
/**
 * Open one thread in the detail pane.
 *
 * This highlights the selected card, then shows the successful and
 * unsuccessful branches side by side with their original branch text
 * and summary cards.
 */
function openThread(thread) {
    activeThread = thread.thread_num;

    // Highlight the selected thread in the list
    document.querySelectorAll('.thread-card').forEach(c => {
        c.classList.toggle('active', +c.dataset.threadNum === activeThread);
    });

    const pane = document.getElementById('detail-pane');

    pane.innerHTML = `
        <div class="detail-header">
            <div class="detail-title-row">
                <h2>Thread <span class="accent">#${thread.thread_num}</span></h2>
                <span class="reviewer-tag">Reviewer ${thread.s?.reviewer_id ?? thread.u?.reviewer_id ?? 'Unknown'}</span>
            </div>
            <p class="detail-subtitle">Compare the <em>successful</em> and <em>unsuccessful</em> summaries for this Reddit debate and their annotation scores.</p>
        </div>

        <div class="summary-grid">
            <div class="thread-column">
                ${originalThreadBox(thread.s, 's')}
                ${summaryCard(thread.s, 's')}
            </div>
            <div class="thread-column">
                ${originalThreadBox(thread.u, 'u')}
                ${summaryCard(thread.u, 'u')}
            </div>
        </div>
    `;

    // Add click behavior for expanding and collapsing summary text
    pane.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.summary-card');
            card.classList.toggle('expanded');
            btn.textContent = card.classList.contains('expanded') ? 'Show less ↑' : 'Read full summary ↓';
        });
    });

    // Add click behavior for expanding and collapsing original thread text
    pane.querySelectorAll('.thread-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const box = btn.closest('.original-thread-box');
            box.classList.toggle('expanded');
            btn.textContent = box.classList.contains('expanded') ? 'Show less ↑' : 'Read full thread ↓';
        });
    });
}

// ── Original thread box ────────────────────────────────────────────────────────
/**
 * Build the original thread box for either the successful or unsuccessful side.
 *
 * This shows the source branch text that the summary came from, so users can
 * compare the summary against the original discussion.
 */
function originalThreadBox(variant, type) {
    if (!variant) {
        return `<div class="original-thread-box original-thread-box--missing">
            <div class="original-thread-label">${type === 's' ? 'Original Successful Branch' : 'Original Unsuccessful Branch'}</div>
            <div class="missing-text">No original thread text available for this variant.</div>
        </div>`;
    }

    const label = type === 's' ? 'Original Successful Branch' : 'Original Unsuccessful Branch';
    const sourceText = (variant.source_text || '').trim();

    if (!sourceText) {
        return `<div class="original-thread-box original-thread-box--missing">
            <div class="original-thread-label">${label}</div>
            <div class="missing-text">No original thread text available for this variant.</div>
        </div>`;
    }

    // Show a shorter preview first, but keep the full text available
    const shortText = sourceText.substring(0, 900).replace(/\n/g, '<br>');
    const fullText = sourceText.replace(/\n/g, '<br>');

    return `
    <div class="original-thread-box">
        <div class="original-thread-label">${label}</div>
        <div class="original-thread-text-box">
            <div class="original-thread-preview">${shortText}…</div>
            <div class="original-thread-full">${fullText}</div>
            <button class="thread-toggle-btn">Read full thread ↓</button>
        </div>
    </div>`;
}

// ── Build a summary card ───────────────────────────────────────────────────────
/**
 * Build the summary card for one side of the thread.
 *
 * This shows the summary text, the annotation scores, and some small metadata
 * like the branch id and reviewer id.
 */
function summaryCard(variant, type) {
    if (!variant) {
        return `<div class="summary-card summary-card--${type} summary-card--missing">
            <div class="card-label">${type === 's' ? '✓ Successful' : '✗ Unsuccessful'}</div>
            <p class="missing-text">No annotation available for this variant.</p>
        </div>`;
    }

    const typeLabel = type === 's' ? '✓ Successful argument' : '✗ Unsuccessful argument';
    const summaryText = (variant.summary || '').trim();

    if (!summaryText) {
        return `
        <div class="summary-card summary-card--${type}">
            <div class="card-label">${typeLabel}</div>

            <div class="scores-row">
                ${scoreBlock('Sentiment', variant.sentiment, 'sentiment')}
                ${scoreBlock('Accuracy', variant.accuracy, 'scale2')}
                ${scoreBlock('Brevity', variant.brevity, 'scale2')}
            </div>

            <div class="summary-text-box">
                <div class="missing-text">No summary text available for this variant.</div>
            </div>

            <div class="meta-row">
                <span class="meta-item">ID: <strong>${variant.arg_id}</strong></span>
                <span class="meta-item">Reviewer: <strong>${variant.reviewer_id}</strong></span>
            </div>
        </div>`;
    }

    // Show a short preview first, then let the user expand the full summary
    const shortText = summaryText.substring(0, 340).replace(/\n/g, '<br>');
    const fullText = summaryText.replace(/\n/g, '<br>');

    return `
    <div class="summary-card summary-card--${type}">
        <div class="card-label">${typeLabel}</div>

        <div class="scores-row">
            ${scoreBlock('Sentiment', variant.sentiment, 'sentiment')}
            ${scoreBlock('Accuracy', variant.accuracy, 'scale2')}
            ${scoreBlock('Brevity', variant.brevity, 'scale2')}
        </div>

        <div class="summary-text-box">
            <div class="summary-preview">${shortText}…</div>
            <div class="summary-full">${fullText}</div>
            <button class="toggle-btn">Read full summary ↓</button>
        </div>

        <div class="meta-row">
            <span class="meta-item">ID: <strong>${variant.arg_id}</strong></span>
            <span class="meta-item">Reviewer: <strong>${variant.reviewer_id}</strong></span>
        </div>
    </div>`;
}

// ── Score block ────────────────────────────────────────────────────────────────
/**
 * Build one score block for sentiment, accuracy, or brevity.
 *
 * This creates the label, the text display, and the visual bar used in each
 * summary card.
 */
function scoreBlock(label, value, kind) {
    let level, display, width;

    if (kind === 'sentiment') {
        level = value === 1 ? 'high' : 'low';
        display = value === 1 ? 'Correct (1)' : 'Incorrect (0)';
        width = value * 100;
    } else {
        if (value === 2) {
            level = 'high';
            display = 'High (2)';
        } else if (value === 1) {
            level = 'medium';
            display = 'Medium (1)';
        } else {
            level = 'low';
            display = 'Low (0)';
        }
        width = (value / 2) * 100;
    }

    return `
    <div class="score-block score-${level}">
        <span class="score-label">${label}</span>
        <span class="score-value">${display}</span>
        <div class="score-bar">
            <div class="score-fill" style="width:${width}%"></div>
        </div>
    </div>`;
}

// ── UI helpers ─────────────────────────────────────────────────────────────────
/**
 * Visually show or hide a loading state for the results list.
 *
 * This does not remove the content. It just fades it while a request is running.
 */
function setResultsLoading(on) {
    document.getElementById('results-container').style.opacity = on ? '0.4' : '1';
}

/**
 * Show an error message in the results area.
 *
 * This is used when the page cannot connect to the back end or when a search fails.
 */
function showResultsError(msg) {
    document.getElementById('results-container').innerHTML =
        `<div class="empty-state"><p class="error-msg">${msg}</p></div>`;
}

/**
 * Delay repeated function calls until the user pauses.
 *
 * This helps avoid sending lots of search requests while the user is still typing.
 */
function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}