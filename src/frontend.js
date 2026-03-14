// ── State ──────────────────────────────────────────────────────────────────────
let allThreads   = [];   // full dataset loaded on boot
let activeThread = null; // currently open thread number

// ── Boot ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadAllThreads();

    document.getElementById('search-input').addEventListener('input', debounce(filterThreads, 220));
    document.getElementById('search-btn').addEventListener('click', filterThreads);
    document.getElementById('search-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') filterThreads();
    });
});

// ── Data loading ───────────────────────────────────────────────────────────────
async function loadAllThreads() {
    setResultsLoading(true);
    try {
        const res  = await fetch('/threads');
        allThreads = await res.json();
        renderThreadList(allThreads);
    } catch (err) {
        showResultsError('Could not connect to backend. Is uvicorn running?');
    } finally {
        setResultsLoading(false);
    }
}

// ── Search / filter ────────────────────────────────────────────────────────────
async function filterThreads() {
    const q = document.getElementById('search-input').value.trim();
    setResultsLoading(true);
    try {
        const url = q ? `/threads?q=${encodeURIComponent(q)}` : '/threads';
        const res = await fetch(url);
        const threads = await res.json();
        renderThreadList(threads);
        // Update count badge
        document.getElementById('result-count').textContent =
            `${threads.length} thread${threads.length !== 1 ? 's' : ''}`;
    } catch (err) {
        showResultsError('Search failed.');
    } finally {
        setResultsLoading(false);
    }
}

// ── Render thread list ─────────────────────────────────────────────────────────
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

        // Derive a topic snippet from the _s summary (or _u if _s missing)
        const anchor = thread.s || thread.u;
        const snippet = anchor ? anchor.summary.substring(0, 90).replace(/\n/g, ' ') + '…' : '—';

        // Score pills for whichever variants exist
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

// Compact pill showing avg score for a variant
function scorePill(label, variant) {
    const sentClass = variant.sentiment === 1 ? 'good' : 'bad';
    return `<span class="pill pill-${label.toLowerCase()} pill-sent-${sentClass}" title="Sentiment:${variant.sentiment} Accuracy:${variant.accuracy} Brevity:${variant.brevity}">${label}</span>`;
}

// ── Open thread detail ─────────────────────────────────────────────────────────
function openThread(thread) {
    activeThread = thread.thread_num;

    // Highlight active card
    document.querySelectorAll('.thread-card').forEach(c => {
        c.classList.toggle('active', +c.dataset.threadNum === activeThread);
    });

    const pane = document.getElementById('detail-pane');

    pane.innerHTML = `
        <div class="detail-header">
            <div class="detail-title-row">
                <h2>Thread <span class="accent">#${thread.thread_num}</span></h2>
                <span class="reviewer-tag">Reviewer ${thread.s?.reviewer_id ?? thread.u?.reviewer_id}</span>
            </div>
            <p class="detail-subtitle">Compare the <em>successful</em> and <em>unsuccessful</em> summaries for this Reddit debate — and their annotation scores.</p>
        </div>

        <div class="summary-grid">
            ${summaryCard(thread.s, 's')}
            ${summaryCard(thread.u, 'u')}
        </div>
    `;

    // Expand/collapse full summary
    pane.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.summary-card');
            card.classList.toggle('expanded');
            btn.textContent = card.classList.contains('expanded') ? 'Show less ↑' : 'Read full summary ↓';
        });
    });
}

// ── Build a summary card (s or u) ─────────────────────────────────────────────
function summaryCard(variant, type) {
    if (!variant) {
        return `<div class="summary-card summary-card--${type} summary-card--missing">
            <div class="card-label">${type === 's' ? '✓ Successful' : '✗ Unsuccessful'}</div>
            <p class="missing-text">No annotation available for this variant.</p>
        </div>`;
    }

    const typeLabel  = type === 's' ? '✓ Successful argument' : '✗ Unsuccessful argument';
    const shortText  = variant.summary.substring(0, 340).replace(/\n/g, '<br>');
    const fullText   = variant.summary.replace(/\n/g, '<br>');

    return `
    <div class="summary-card summary-card--${type}">
        <div class="card-label">${typeLabel}</div>

        <div class="scores-row">
            ${scoreBlock('Sentiment', variant.sentiment, 'sentiment')}
            ${scoreBlock('Accuracy',  variant.accuracy,  'scale2')}
            ${scoreBlock('Brevity',   variant.brevity,   'scale2')}
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
function scoreBlock(label, value, kind) {
    let level, display;

    if (kind === 'sentiment') {
        level   = value === 1 ? 'high' : 'low';
        display = value === 1 ? 'Positive (1)' : 'Negative (0)';
    } else {
        // scale2: 1 = lower, 2 = higher
        level   = value === 2 ? 'high' : 'medium';
        display = value === 2 ? 'High (2)' : 'Low (1)';
    }

    return `
    <div class="score-block score-${level}">
        <span class="score-label">${label}</span>
        <span class="score-value">${display}</span>
        <div class="score-bar">
            <div class="score-fill" style="width:${kind === 'sentiment' ? value * 100 : (value / 2) * 100}%"></div>
        </div>
    </div>`;
}

// ── UI helpers ─────────────────────────────────────────────────────────────────
function setResultsLoading(on) {
    document.getElementById('results-container').style.opacity = on ? '0.4' : '1';
}

function showResultsError(msg) {
    document.getElementById('results-container').innerHTML =
        `<div class="empty-state"><p class="error-msg">${msg}</p></div>`;
}

function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
