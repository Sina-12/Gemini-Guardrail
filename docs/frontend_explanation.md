# frontend.js — Technical Documentation

## Overview

`frontend.js` drives the client-side behaviour of a corpus browser for Reddit r/ChangeMyView (CMV) argument threads. It is a vanilla JavaScript single-page application (no framework) that communicates with a Python back end (a `uvicorn`-served FastAPI server) via a small REST API. The UI presents a two-panel layout: a filterable thread list on the left and a side-by-side detail view on the right.

---

## Global State

```js
let allThreads   = [];
let activeThread = null;
```

| Variable | Type | Purpose |
|---|---|---|
| `allThreads` | `Array<Object>` | Full thread dataset fetched on page load. Retained in memory so the list can be re-rendered without a network round-trip if needed. |
| `activeThread` | `number \| null` | The `thread_num` of whichever thread is currently open in the detail pane. Used to keep the matching card highlighted in the list. |

---

## Initialisation — `DOMContentLoaded`

```js
document.addEventListener('DOMContentLoaded', () => { … });
```

Fires once the HTML is parsed. It performs three tasks:

1. Calls `loadAllThreads()` to populate the list immediately.
2. Attaches a **debounced `input` listener** on `#search-input` — triggers `filterThreads` 220 ms after the user stops typing.
3. Attaches a **`click` listener** on `#search-btn` and a **`keydown` listener** on `#search-input` (Enter key) — both call `filterThreads` directly.

---

## Data Loading

### `loadAllThreads()`

```
GET /threads
→ JSON array of thread objects
```

- Sets the results container to 40 % opacity while the request is in flight (`setResultsLoading(true)`).
- On success, writes the response into `allThreads` and calls `renderThreadList`.
- On failure (network error or non-OK response), calls `showResultsError` with a hint about `uvicorn`.
- Restores opacity in a `finally` block regardless of outcome.

---

## Search and Filtering

### `filterThreads()`

```
GET /threads          (when search box is empty)
GET /threads?q=<term> (when a keyword is present)
→ JSON array of thread objects
```

- Reads the current value of `#search-input`, trims whitespace, and builds the appropriate URL.
- Calls `renderThreadList` with the returned subset.
- Updates `#result-count` with a correctly pluralised thread count string.
- Uses the same loading/error pattern as `loadAllThreads`.

> **Note:** Filtering is entirely server-side. The client sends the raw query string and displays whatever the back end returns. `allThreads` is **not** filtered in memory.

---

## Rendering

### `renderThreadList(threads)`

Clears and rebuilds `#results-container` from scratch on every call.

- Updates `#result-count`.
- If `threads` is empty, injects an `.empty-state` placeholder.
- Otherwise, for each thread object it creates a `.thread-card` `<div>` containing:
  - A header row with the thread number and two score pills (S and U).
  - A 90-character snippet derived from `thread.s.source_text` → `thread.s.summary` → `thread.u.source_text` → `thread.u.summary` (first truthy value).
- Cards whose `thread_num` matches `activeThread` receive the `.active` CSS class.
- Each card has a `click` listener that calls `openThread(thread)`.

### `scorePill(label, variant)`

Returns an HTML string for a small badge. The pill's CSS class encodes:
- Which side it represents (`pill-s` or `pill-u`).
- Whether the sentiment score is correct (`pill-sent-good` for `1`, `pill-sent-bad` for `0`).

A `title` attribute exposes all three raw scores (sentiment, accuracy, brevity) as a tooltip.

---

## Detail Pane

### `openThread(thread)`

Sets `activeThread` to the selected thread's number, re-applies `.active` to the correct card in the list, then rebuilds `#detail-pane` with:

1. A **header** — thread number, reviewer ID, and a descriptive subtitle.
2. A **`.summary-grid`** containing two `.thread-column` elements, one for the successful (`s`) branch and one for the unsuccessful (`u`) branch. Each column contains:
   - An **original thread box** (`originalThreadBox`).
   - A **summary card** (`summaryCard`).

After injecting the HTML, two sets of toggle listeners are wired up:

| Button class | Target container | Effect |
|---|---|---|
| `.toggle-btn` | `.summary-card` | Toggles `.expanded`; swaps button label between *"Read full summary ↓"* and *"Show less ↑"*. |
| `.thread-toggle-btn` | `.original-thread-box` | Same pattern for the original thread text. |

### `originalThreadBox(variant, type)`

Generates the collapsible box that shows the raw Reddit branch text.

- Returns a `--missing` placeholder if `variant` is falsy or `variant.source_text` is empty.
- Otherwise renders two sibling `<div>`s:
  - `.original-thread-preview` — first 900 characters with newlines converted to `<br>`.
  - `.original-thread-full` — the complete text.
- Visibility between preview and full is controlled purely by CSS (toggled via the `.expanded` class on the parent `.original-thread-box`).

### `summaryCard(variant, type)`

Generates the annotation card shown below the original thread box.

- Returns a `--missing` placeholder if `variant` is falsy.
- Renders three **score blocks** (sentiment, accuracy, brevity) via `scoreBlock`.
- Renders the summary text with the same preview / full / toggle pattern as `originalThreadBox` (340-character preview).
- Renders a metadata row with `arg_id` and `reviewer_id`.

### `scoreBlock(label, value, kind)`

Builds a single score display element containing a label, a human-readable value string, and a proportional fill bar.

| `kind` | Scale | Levels |
|---|---|---|
| `'sentiment'` | 0–1 (binary) | `high` (correct, 1) / `low` (incorrect, 0) |
| `'scale2'` | 0–2 (integer) | `high` (2) / `medium` (1) / `low` (0) |

Bar width is calculated as a percentage of the maximum possible value (`value * 100` for sentiment, `(value / 2) * 100` for scale-2 scores).

---

## Utility Functions

### `setResultsLoading(on)`

Toggles the opacity of `#results-container` between `0.4` (loading) and `1` (done). Does not remove or replace existing content, so the list remains readable during fast refreshes.

### `showResultsError(msg)`

Replaces the contents of `#results-container` with an `.empty-state` div containing the supplied error string.

### `debounce(fn, ms)`

Standard trailing-edge debounce. Returns a wrapper function that resets a `setTimeout` on every call and only invokes `fn` once the wrapper has not been called for `ms` milliseconds.

---

## Expected API Shape

The back end must expose:

```
GET /threads
GET /threads?q=<string>
```

Both endpoints return a JSON array of **thread objects** with the following structure:

```jsonc
{
  "thread_num": 42,
  "s": {                        // successful branch (may be null)
    "arg_id": "abc123",
    "reviewer_id": "r01",
    "source_text": "…",         // original Reddit branch text
    "summary": "…",             // annotator-written summary
    "sentiment": 1,             // 0 or 1
    "accuracy": 2,              // 0, 1, or 2
    "brevity": 1                // 0, 1, or 2
  },
  "u": { … }                    // unsuccessful branch, same shape
}
```

Either `s` or `u` (but not necessarily both) may be `null` for a given thread; the UI handles both missing-variant cases gracefully.

---

## Data Flow Diagram

Credit to Claude for formatting this.

```
DOMContentLoaded
      │
      ├─► loadAllThreads() ──► GET /threads ──► renderThreadList()
      │
      └─► [user types / clicks search]
                │
                └─► filterThreads() ──► GET /threads?q=… ──► renderThreadList()
                                                                      │
                                                               [user clicks card]
                                                                      │
                                                               openThread()
                                                                      │
                                                          ┌──────────┴──────────┐
                                                  originalThreadBox()    summaryCard()
                                                                              │
                                                                        scoreBlock() ×3
```
