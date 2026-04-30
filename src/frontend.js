let allThreads = [];
let activeThreadId = null;
let activeVariant = "s";
let tooltipEl = null;
let activeSocket = null;
let activeRunId = 0;
let previousSummaryLines = [];

const PALETTE = ["#65d8ff", "#a797ff", "#73ffa6", "#ffd166", "#ff8aa1", "#9dd4ff"];

document.addEventListener("DOMContentLoaded", () => {
    loadThreads();
    document.getElementById("search-input").addEventListener("input", debounce(filterThreads, 220));
    document.getElementById("search-btn").addEventListener("click", filterThreads);
    document.getElementById("search-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter") filterThreads();
    });
    window.addEventListener("beforeunload", () => closeActiveSocket());
});

async function loadThreads() {
    try {
        const response = await fetch("/threads");
        allThreads = await response.json();
        renderThreadList(allThreads);
    } catch (_) {
        showListError("Backend unreachable. Start FastAPI with uvicorn.");
    }
}

async function filterThreads() {
    const q = document.getElementById("search-input").value.trim();
    const endpoint = q ? `/threads?q=${encodeURIComponent(q)}` : "/threads";
    try {
        const response = await fetch(endpoint);
        const rows = await response.json();
        renderThreadList(rows);
    } catch (_) {
        showListError("Search failed.");
    }
}

function renderThreadList(threads) {
    const list = document.getElementById("results-container");
    document.getElementById("result-count").textContent = `${threads.length}`;
    if (!threads.length) {
        list.innerHTML = `<div class="empty-state">No matching threads.</div>`;
        return;
    }
    list.innerHTML = "";
    threads.forEach((thread) => {
        const sample = thread.s || thread.u;
        const snippet = ((sample?.source_text || sample?.summary || "").replace(/\s+/g, " ").trim().slice(0, 94) || "No text") + "...";
        const card = document.createElement("button");
        card.type = "button";
        card.className = `thread-card ${thread.thread_num === activeThreadId ? "active" : ""}`;
        card.innerHTML = `
            <div class="thread-top">
                <span class="thread-id">Thread #${thread.thread_num}</span>
                <span class="chip">${thread.s ? "S" : ""}${thread.s && thread.u ? " / " : ""}${thread.u ? "U" : ""}</span>
            </div>
            <p class="thread-snippet">${escapeHtml(snippet)}</p>
        `;
        card.addEventListener("click", () => openThread(thread));
        list.appendChild(card);
    });
}

function openThread(thread) {
    activeThreadId = thread.thread_num;
    if (!thread[activeVariant]) activeVariant = thread.s ? "s" : "u";
    renderThreadList(allThreads);
    renderCommandCenter(thread);
}

function renderCommandCenter(thread) {
    const pane = document.getElementById("detail-pane");
    const variant = thread[activeVariant];
    if (!variant) {
        pane.innerHTML = `<div class="empty-center">Selected variant has no data.</div>`;
        return;
    }

    pane.innerHTML = `
        <div class="command-grid">
            <div class="center-col">
                <div class="top-kpis">
                    <section class="panel trust-panel">
                        <h3 class="panel-title">Dynamic Trust Score</h3>
                        <div class="trust-row"><span>Live confidence</span><strong id="trust-percent">50%</strong></div>
                        <div class="trust-track"><div id="trust-fill" class="trust-fill"></div></div>
                        <div class="run-actions">
                            <button id="run-audit-btn" class="run-btn">Run Live Audit Stream</button>
                            <span id="run-status" class="status-pill">Ready</span>
                        </div>
                    </section>
                    <section class="panel ring-panel">
                        <div class="ring-wrap">
                            <svg width="110" height="110" viewBox="0 0 110 110">
                                <defs>
                                    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stop-color="#ff9046"></stop>
                                        <stop offset="55%" stop-color="#ffe070"></stop>
                                        <stop offset="100%" stop-color="#34f79f"></stop>
                                    </linearGradient>
                                </defs>
                                <circle class="ring-bg" cx="55" cy="55" r="45"></circle>
                                <circle id="ring-fg" class="ring-fg" cx="55" cy="55" r="45" stroke-dasharray="${2 * Math.PI * 45}" stroke-dashoffset="${2 * Math.PI * 45 * 0.5}"></circle>
                            </svg>
                            <div id="ring-value" class="ring-value">50</div>
                        </div>
                    </section>
                </div>
                <div class="variant-switch">
                    <button id="variant-s" class="${activeVariant === "s" ? "active" : ""}" ${thread.s ? "" : "disabled"}>Successful branch</button>
                    <button id="variant-u" class="${activeVariant === "u" ? "active" : ""}" ${thread.u ? "" : "disabled"}>Unsuccessful branch</button>
                </div>
                <section class="panel compare-panel">
                    <div class="surface-title"><span>Forensic Layer Linkage</span><span id="layer-status">Idle</span></div>
                    <div class="layer-flow">
                        <div class="flow-node" data-layer="summarizer">Prepared Summary / Phi-4 Mini Rewrite</div>
                        <div class="flow-link"></div>
                        <div class="flow-node" data-layer="semantic">Semantic Retrieval</div>
                        <div class="flow-link"></div>
                        <div class="flow-node" data-layer="deberta">DeBERTa Scan</div>
                        <div class="flow-link"></div>
                        <div class="flow-node" data-layer="judge">Phi-4 Judge</div>
                    </div>
                </section>
                <div class="compare-grid">
                    <section class="panel compare-panel">
                        <div class="surface-title"><span>Source Text</span><span id="source-count">0 lines</span></div>
                        <div id="source-lines" class="source-lines"></div>
                    </section>
                    <section class="panel compare-panel">
                        <div class="surface-title"><span>Summary Heatmap</span><span id="summary-count">0 claims</span></div>
                        <div id="summary-lines" class="summary-lines"></div>
                        <div class="surface-title" style="margin-top:10px;"><span>New Summary</span><span id="new-summary-count">0 claims</span></div>
                        <div id="new-summary-lines" class="summary-lines"></div>
                    </section>
                </div>
            </div>
            <aside class="panel feed-panel">
                <div class="feed-head">
                    <h3>Live Forensic Feed</h3>
                    <p>Streaming internal pipeline actions</p>
                </div>
                <div id="feed-list" class="feed-list"></div>
            </aside>
        </div>
    `;

    renderSource(variant.source_text);
    bindVariantSwitch(thread);
    bindRunAudit(thread);
    ensureTooltip();
}

function bindVariantSwitch(thread) {
    const sBtn = document.getElementById("variant-s");
    const uBtn = document.getElementById("variant-u");
    if (sBtn) sBtn.addEventListener("click", () => { if (thread.s) { activeVariant = "s"; renderCommandCenter(thread); } });
    if (uBtn) uBtn.addEventListener("click", () => { if (thread.u) { activeVariant = "u"; renderCommandCenter(thread); } });
}

function bindRunAudit(thread) {
    const runBtn = document.getElementById("run-audit-btn");
    runBtn.addEventListener("click", async () => {
        const variant = thread[activeVariant];
        if (!variant?.source_text || !variant?.summary) return;
        activeRunId += 1;
        const runId = activeRunId;
        closeActiveSocket();
        runBtn.disabled = true;
        setStatus("Connecting stream");
        setTrust(0.5);
        clearSummary();
        clearFeed();
        resetFlow();
        const result = await streamGuardrail(variant.source_text, variant.summary, runBtn, runId);
        if (runId !== activeRunId) return;
        if (!result.ok) {
            setStatus("Error");
            pushFeed(`Pipeline error: ${result.error}`);
            runBtn.disabled = false;
        }
    });
}

async function streamGuardrail(sourceText, summaryText, runBtn, runId) {
    return new Promise((resolve) => {
        const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
        const ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws/guardrail/phase1`);
        activeSocket = ws;
        let done = false;
        let watchdog = null;
        const settle = (payload) => {
            if (done) return;
            done = true;
            if (watchdog) clearTimeout(watchdog);
            runBtn.disabled = false;
            resolve(payload);
        };
        // Pipeline can run many minutes (per-claim DeBERTa + Ollama judge/rewrite × iterations).
        // Only fail if the socket goes silent for a long time (no heartbeats/events).
        const STALL_MS = 45 * 60 * 1000;
        const bumpWatchdog = () => {
            if (watchdog) clearTimeout(watchdog);
            watchdog = setTimeout(() => {
                if (runId !== activeRunId) return;
                try { ws.close(); } catch (_) {}
                settle({
                    ok: false,
                    error:
                        "Stream stalled: no messages for 45 minutes. Check Ollama and server logs.",
                });
            }, STALL_MS);
        };
        bumpWatchdog();

        ws.onopen = () => {
            setStatus("Running live");
            pushFeed("Live stream connected.");
            bumpWatchdog();
            ws.send(
                JSON.stringify({
                    source_text: sourceText,
                    summary: summaryText,
                    max_iters: 3,
                    min_support_ratio: 0.86,
                })
            );
        };

        ws.onmessage = (message) => {
            let packet = null;
            try { packet = JSON.parse(message.data); } catch (_) { return; }
            bumpWatchdog();
            if (packet.type === "heartbeat") { pulseWaiting(); return; }
            if (packet.type === "error") {
                ws.close();
                settle({ ok: false, error: packet.detail || "Stream error." });
                return;
            }
            if (packet.type === "event") {
                handleStreamEvent(packet.event);
                return;
            }
            if (packet.type === "complete") {
                const result = packet.result || {};
                setStatus(`Completed • ${result.status || "done"}`);
                setTrust(result.trust_score ?? 0.5);
                setLayerStatus("Complete");
                ws.close();
                settle({ ok: true, data: result });
            }
        };

        ws.onerror = () => {
            settle({ ok: false, error: "WebSocket failed to connect." });
        };
        ws.onclose = () => {
            if (!done) settle({ ok: false, error: "WebSocket closed unexpectedly." });
        };
    });
}

async function handleStreamEvent(event) {
    if (!event?.type) return;
    const label = event.iteration ? `Iter ${event.iteration}` : "Run";
    switch (event.type) {
        case "run_started":
            setLayerStatus("Booting");
            pushFeed(`${label}: Pipeline initialized.`);
            break;
        case "iteration_started":
            setStatus(`Iteration ${event.iteration}`);
            pushFeed(`${label}: Iteration started.`);
            break;
        case "summarizer_start":
            activateLayer("summarizer", true);
            setLayerStatus("Preparing/revising summary");
            pushFeed(`${label}: Summary stage started...`, true);
            break;
        case "summarizer_complete":
            activateLayer("summarizer", false);
            activateLayer("semantic", true);
            pushFeed(`${label}: Candidate summary ready.`);
            if (event.target === "new") {
                renderNewSummary(event.candidate_summary || "");
            } else {
                renderSummaryWithDiff(event.candidate_summary || "", event.iteration);
            }
            break;
        case "audit_start":
            setLayerStatus("Claim decomposition");
            pushFeed(`${label}: ${event.claim_count || 0} claims detected.`);
            break;
        case "claim_scored":
            activateLayer("semantic", false);
            activateLayer("deberta", true);
            setLayerStatus("DeBERTa scanning");
            markClaimScored(event);
            if (event.send_to_judge) {
                markSummaryState(event.claim_index, "warn");
                pushFeed(`${label}: Sentence ${Number(event.claim_index) + 1} flagged for mismatch.`, true);
            } else {
                markSummaryState(event.claim_index, "good");
            }
            break;
        case "judge_start":
            activateLayer("deberta", false);
            activateLayer("judge", true);
            setLayerStatus("Phi-4 judge review");
            pushFeed(`${label}: Phi-4 reasoning judging sentence ${Number(event.claim_index) + 1}.`, true);
            break;
        case "judge_result":
            activateLayer("judge", false);
            activateLayer("deberta", true);
            if (event.target === "new") {
                markNewSummaryState(event.claim_index, event.hallucinated ? "bad" : "good");
            } else {
                await typeJudgeReason(
                    event.claim_index,
                    Boolean(event.hallucinated),
                    event.explanation
                );
                markSummaryState(event.claim_index, event.hallucinated ? "bad" : "good");
            }
            break;
        case "new_summary_started":
            pushFeed(`${label}: New summary window initialized.`);
            renderNewSummary(event.candidate_summary || "");
            break;
        case "new_sentence_rewritten":
            pushFeed(
                `${label}: phi4-mini rewrote sentence ${Number(event.claim_index) + 1}. ` +
                `Old: "${String(event.old_sentence || "").slice(0, 120)}" -> ` +
                `New: "${String(event.sentence || "").slice(0, 120)}"`
            );
            break;
        case "new_summary_update":
            renderNewSummary(event.candidate_summary || "");
            break;
        case "claim_finalized":
            markClaimFinal(event);
            break;
        case "audit_complete":
            activateLayer("deberta", false);
            setLayerStatus("Iteration audited");
            pushFeed(`${label}: Audit complete, support=${event.support_ratio}.`);
            break;
        case "trust_updated":
            setTrust(event.trust_score ?? 0.5);
            pushFeed(`${label}: Trust score ${Math.round((event.trust_score || 0) * 100)}%.`);
            break;
        case "run_complete":
            setLayerStatus(`Finished (${event.status})`);
            pushFeed(`${label}: Run complete.`);
            break;
        default:
            pushFeed(`${label}: ${event.type}`);
    }
}

function markClaimScored(event) {
    const summaryEl = document.querySelector(`.summary-line[data-summary-index="${event.claim_index}"]`);
    if (!summaryEl) return;
    const color = PALETTE[Number(event.claim_index) % PALETTE.length];
    summaryEl.style.borderLeft = `3px solid ${color}`;
    summaryEl.dataset.tooltip = `DeBERTa: ${event.deberta_label} (${event.deberta_confidence}) | cosine=${event.cosine_similarity}`;
    bindTooltip(summaryEl);
    summaryEl._evidenceContext = event.evidence_top3 || [];
    summaryEl.onclick = () => toggleEvidenceFocus(summaryEl);
}

function markClaimFinal(event) {
    if (event.verdict === "hallucinated") markSummaryState(event.claim_index, "bad");
    if (event.verdict === "supported") markSummaryState(event.claim_index, "good");
    pushFeed(`Sentence ${Number(event.claim_index) + 1}: ${event.verdict}.`);
}

function activateLayer(layer, active) {
    const node = document.querySelector(`.flow-node[data-layer="${layer}"]`);
    if (!node) return;
    node.classList.toggle("active", active);
    if (!active) node.classList.add("completed");
}

function setLayerStatus(text) {
    const el = document.getElementById("layer-status");
    if (el) el.textContent = text;
}

function resetFlow() {
    document.querySelectorAll(".flow-node").forEach((node) => node.classList.remove("active", "completed"));
    setLayerStatus("Running");
}

function pulseWaiting() {
    const el = document.getElementById("run-status");
    if (!el) return;
    el.classList.add("pulse");
    setTimeout(() => el.classList.remove("pulse"), 250);
}

function closeActiveSocket() {
    if (activeSocket && activeSocket.readyState <= 1) activeSocket.close();
    activeSocket = null;
}

function renderSource(sourceText) {
    const sourceEl = document.getElementById("source-lines");
    const lines = splitSentences(sourceText || "");
    document.getElementById("source-count").textContent = `${lines.length} lines`;
    sourceEl.innerHTML = lines.map((line, idx) => `<div class="line source-line" data-source-index="${idx}">${escapeHtml(line)}</div>`).join("");
}

function renderSummaryWithDiff(summaryText, iteration) {
    clearEvidenceFocus();
    const summaryEl = document.getElementById("summary-lines");
    const lines = splitSentences(summaryText || "");
    document.getElementById("summary-count").textContent = `${lines.length} claims`;
    summaryEl.innerHTML = "";

    const previousSet = new Set(previousSummaryLines.map((line) => normalizeSentence(line)));
    const currentSet = new Set(lines.map((line) => normalizeSentence(line)));
    const removed = previousSummaryLines.filter(
        (line) => !currentSet.has(normalizeSentence(line))
    );

    for (let i = 0; i < lines.length; i += 1) {
        const div = document.createElement("div");
        div.className = "line summary-line";
        div.dataset.summaryIndex = String(i);
        const normalized = normalizeSentence(lines[i]);
        let diffTag = "";
        if (iteration > 1 && !previousSet.has(normalized)) {
            diffTag = `<span class="diff-tag added">added</span>`;
        }
        div.innerHTML = `<span class="summary-text">${escapeHtml(lines[i])}</span>${diffTag}`;
        summaryEl.appendChild(div);
    }

    if (iteration > 1 && removed.length) {
        const removedWrap = document.createElement("div");
        removedWrap.className = "summary-removed-wrap";
        removedWrap.innerHTML = `<div class="summary-removed-title">Removed from previous iteration</div>`;
        removed.forEach((line) => {
            const removedLine = document.createElement("div");
            removedLine.className = "line summary-line removed-line";
            removedLine.textContent = line;
            removedWrap.appendChild(removedLine);
        });
        summaryEl.appendChild(removedWrap);
    }

    previousSummaryLines = lines;
}

function renderNewSummary(summaryText) {
    const summaryEl = document.getElementById("new-summary-lines");
    if (!summaryEl) return;
    const lines = splitSentences(summaryText || "");
    const countEl = document.getElementById("new-summary-count");
    if (countEl) countEl.textContent = `${lines.length} claims`;
    summaryEl.innerHTML = "";
    for (let i = 0; i < lines.length; i += 1) {
        const div = document.createElement("div");
        div.className = "line summary-line";
        div.dataset.summaryIndex = String(i);
        div.innerHTML = `<span class="summary-text">${escapeHtml(lines[i])}</span>`;
        summaryEl.appendChild(div);
    }
}

function renderAuditClaims(claims) {
    const sourceEls = Array.from(document.querySelectorAll(".source-line"));
    const summaryEls = Array.from(document.querySelectorAll(".summary-line"));
    claims.forEach((claim, idx) => {
        const summaryEl = summaryEls[idx];
        if (!summaryEl) return;
        const normalized = normalizeSentence(claim.evidence || "");
        const sourceTarget = sourceEls.find((sourceEl) => normalizeSentence(sourceEl.textContent) === normalized);
        const color = PALETTE[idx % PALETTE.length];

        summaryEl.style.borderLeft = `3px solid ${color}`;
        summaryEl.dataset.score = `${claim.confidence ?? "n/a"}`;
        summaryEl.dataset.tooltip = `DeBERTa confidence: ${claim.confidence ?? "n/a"} | Verdict: ${claim.verdict || "n/a"}`;
        bindTooltip(summaryEl);

        if (sourceTarget) {
            sourceTarget.style.borderLeft = `3px solid ${color}`;
            summaryEl.dataset.sourceIndex = sourceTarget.dataset.sourceIndex || "";
            summaryEl.addEventListener("click", () => jumpToSource(sourceTarget, summaryEl));
        }
    });
}

function normalizeJudgeExplanation(raw) {
    if (raw && typeof raw === "object") {
        const maybe = String(raw.explanation || "").trim();
        return maybe || JSON.stringify(raw);
    }
    const s = String(raw || "").trim();
    if (!s) return "Judge explanation unavailable.";
    try {
        const obj = JSON.parse(s);
        if (obj && typeof obj === "object") {
            const maybe = String(obj.explanation || "").trim();
            return maybe || s;
        }
    } catch (_) {
        // leave as-is
    }
    return s;
}

async function typeJudgeReason(idx, hallucinated, rawExplanation) {
    const target = document.querySelector(`.summary-line[data-summary-index="${idx}"]`);
    if (!target) return;
    const verdictText = hallucinated ? "Hallucinated: Yes." : "Hallucinated: No.";
    const explanation = normalizeJudgeExplanation(rawExplanation);
    const text = `${verdictText} Explanation: ${explanation}`;
    let judgeNode = target.querySelector(".judge-note");
    if (!judgeNode) {
        judgeNode = document.createElement("div");
        judgeNode.className = "typewriter judge-note";
        judgeNode.style.marginTop = "7px";
        judgeNode.style.color = "#a7b8d3";
        judgeNode.style.fontSize = "11px";
        judgeNode.style.fontFamily = '"JetBrains Mono", monospace';
        target.appendChild(judgeNode);
    }
    judgeNode.textContent = "";
    await typeInto(judgeNode, text, 4);
}

function markSummaryState(idx, kind) {
    const line = document.querySelector(`.summary-line[data-summary-index="${idx}"]`);
    if (!line) return;
    line.classList.remove("warn", "bad", "good");
    line.classList.add(kind);
}

function markNewSummaryState(idx, kind) {
    const lines = document.querySelectorAll("#new-summary-lines .summary-line");
    const line = lines[Number(idx)];
    if (!line) return;
    line.classList.remove("warn", "bad", "good");
    line.classList.add(kind);
}

function clearEvidenceFocus() {
    const sourceWrap = document.getElementById("source-lines");
    if (sourceWrap) sourceWrap.classList.remove("is-evidence-focus");
    document.querySelectorAll(".source-line.evidence-focus").forEach((el) => {
        el.classList.remove("evidence-focus");
    });
    document.querySelectorAll(".summary-line.linked").forEach((el) => {
        el.classList.remove("linked");
    });
}

function toggleEvidenceFocus(summaryEl) {
    const sourceWrap = document.getElementById("source-lines");
    if (!sourceWrap) return;
    const ctx = summaryEl._evidenceContext || [];
    if (summaryEl.classList.contains("linked")) {
        clearEvidenceFocus();
        return;
    }
    clearEvidenceFocus();
    const norms = new Set(ctx.map((s) => normalizeSentence(s)));
    const sourceEls = Array.from(document.querySelectorAll(".source-line"));
    const targets = sourceEls.filter((s) => norms.has(normalizeSentence(s.textContent)));
    if (!targets.length) return;
    sourceWrap.classList.add("is-evidence-focus");
    sourceEls.forEach((el) => el.classList.remove("evidence-focus"));
    targets.forEach((el) => el.classList.add("evidence-focus"));
    summaryEl.classList.add("linked");
    targets[0].scrollIntoView({ behavior: "smooth", block: "center" });
}

function jumpToSource(sourceEl, summaryEl) {
    document.querySelectorAll(".line.linked").forEach((line) => line.classList.remove("linked"));
    sourceEl.classList.add("linked");
    summaryEl.classList.add("linked");
    sourceEl.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearSummary() {
    clearEvidenceFocus();
    const el = document.getElementById("summary-lines");
    if (el) {
        el.innerHTML = `<div class="empty-state">Summary output will stream here...</div>`;
    }
    const newEl = document.getElementById("new-summary-lines");
    if (newEl) {
        newEl.innerHTML = `<div class="empty-state">Rewritten summary appears here if hallucinations are found...</div>`;
    }
    const newCountEl = document.getElementById("new-summary-count");
    if (newCountEl) newCountEl.textContent = "0 claims";
    previousSummaryLines = [];
}

function setTrust(value) {
    const score = Math.max(0, Math.min(1, Number(value) || 0));
    const pct = Math.round(score * 100);
    const fill = document.getElementById("trust-fill");
    const percentEl = document.getElementById("trust-percent");
    const ringVal = document.getElementById("ring-value");
    const ringFg = document.getElementById("ring-fg");
    if (fill) fill.style.width = `${pct}%`;
    if (percentEl) percentEl.textContent = `${pct}%`;
    if (ringVal) ringVal.textContent = String(pct);
    if (ringFg) {
        const c = 2 * Math.PI * 45;
        ringFg.style.strokeDashoffset = String(c * (1 - score));
    }
}

function setStatus(text) {
    const el = document.getElementById("run-status");
    if (el) el.textContent = text;
}

function clearFeed() {
    const feed = document.getElementById("feed-list");
    if (feed) feed.innerHTML = "";
}

function pushFeed(message, looping = false) {
    const feed = document.getElementById("feed-list");
    if (!feed) return;
    const item = document.createElement("div");
    item.className = `feed-item ${looping ? "looping active" : ""}`;
    item.textContent = `[${stamp()}] ${message}`;
    feed.appendChild(item);
    feed.scrollTop = feed.scrollHeight;
    if (looping) {
        setTimeout(() => item.classList.remove("looping", "active"), 900);
    }
}

function showListError(message) {
    const list = document.getElementById("results-container");
    list.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function splitSentences(text) {
    const raw = String(text || "").trim();
    if (!raw) return [];
    const masked = [];
    const ph = (i) => `\uE000${i}\uE001`;
    let s = raw.replace(/\r\n/g, "\n");

    const protect = (regex) => {
        s = s.replace(regex, (match) => {
            masked.push(match);
            return ph(masked.length - 1);
        });
    };
    protect(/https?:\/\/[^\s]+/gi);
    protect(/\b\d+\.\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/g);
    protect(/\b(?:e\.g\.|i\.e\.|et al\.|vs\.|etc\.|approx\.|ca\.|figs?\.|dr\.|mr\.|mrs\.|ms\.|prof\.|ph\.d\.|sr\.|jr\.|st\.|ave\.|blvd\.|no\.|vol\.|pp?\.|chs?\.|secs?\.|eds?\.|inc\.|ltd\.|co\.|corp\.|u\.s\.a?\.|u\.k\.|e\.u\.|a\.m\.|p\.m\.|viz\.|cf\.|b\.c\.|a\.d\.|c\.e\.)\b/gi);
    const parts = s.split(/(?<=[.!?])\s+/).map((part) => part.trim()).filter(Boolean);
    return parts.map((part) => part.replace(/\uE000(\d+)\uE001/g, (_, i) => masked[Number(i)]));
}

async function typeInto(element, text, delay = 8) {
    if (!element) return;
    let i = 0;
    while (i < text.length) {
        element.textContent += text[i];
        i += 1;
        await sleep(delay);
    }
}

function ensureTooltip() {
    if (tooltipEl) return;
    tooltipEl = document.createElement("div");
    tooltipEl.className = "tooltip";
    document.body.appendChild(tooltipEl);
}

function bindTooltip(node) {
    node.addEventListener("mouseenter", () => {
        tooltipEl.textContent = node.dataset.tooltip || "";
        tooltipEl.style.display = "block";
    });
    node.addEventListener("mousemove", (event) => {
        tooltipEl.style.left = `${event.clientX + 16}px`;
        tooltipEl.style.top = `${event.clientY + 16}px`;
    });
    node.addEventListener("mouseleave", () => {
        tooltipEl.style.display = "none";
    });
}

function normalizeSentence(text) {
    return String(text || "").toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
}

function stamp() {
    const d = new Date();
    return d.toTimeString().slice(0, 8);
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}