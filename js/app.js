/**
 * Comb-Search — Frontend
 *
 * Minimal academic paper list:
 * - Date picker (top right)
 * - Search box (toggle via magnifier)
 * - Compact arXiv-style paper rows with inline expansion
 * - Matched papers get a subtle dot (no reason exposed)
 * - Bottom trend bar
 */

// ── State ────────────────────────────────────────────────
let availableDates = [];
let currentDate = '';
let allPapers = [];          // all papers loaded for current date(s)
let filteredPapers = [];     // after search filtering
let expandedId = null;       // currently expanded paper id
let flatpickrInstance = null;
let searchQuery = '';

// ── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initFlatpickr();
    initSearch();
    fetchAvailableDates().then(() => {
        if (availableDates.length > 0) {
            loadDate(availableDates[0]);
        }
    });
    fetchTrend();
});

// ── Flatpickr ────────────────────────────────────────────
function initFlatpickr() {
    const input = document.getElementById('flatpickrInput');
    flatpickrInstance = flatpickr(input, {
        dateFormat: 'Y-m-d',
        defaultDate: new Date(),
        onChange: function(selectedDates, dateStr) {
            if (dateStr) {
                hideDatePicker();
                loadDate(dateStr);
            }
        }
    });
    // Hide the flatpickr input visually, use our button to toggle
    input.style.position = 'absolute';
    input.style.opacity = '0';
    input.style.pointerEvents = 'none';
    input.style.width = '1px';
    input.style.height = '1px';
}

document.getElementById('dateBtn').addEventListener('click', () => {
    const popup = document.getElementById('datePicker');
    popup.classList.toggle('hidden');
    if (!popup.classList.contains('hidden')) {
        flatpickrInstance.open();
    }
});

function hideDatePicker() {
    document.getElementById('datePicker').classList.add('hidden');
}

// ── Search ───────────────────────────────────────────────
function initSearch() {
    const toggle = document.getElementById('searchToggle');
    const bar = document.getElementById('searchBar');
    const input = document.getElementById('searchInput');

    toggle.addEventListener('click', () => {
        bar.classList.toggle('hidden');
        if (!bar.classList.contains('hidden')) {
            input.focus();
        } else {
            input.value = '';
            searchQuery = '';
            applySearch();
        }
    });

    input.addEventListener('input', () => {
        searchQuery = input.value.trim().toLowerCase();
        applySearch();
    });
}

function applySearch() {
    if (searchQuery === '') {
        filteredPapers = [...allPapers];
    } else {
        filteredPapers = allPapers.filter(p => {
            const hay = [
                p.title, p.authors, p.summary, p.id,
                p.tldr || '', p.motivation || '', p.method || '',
                p.result || '', p.conclusion || '', p.future_work || ''
            ].join(' ').toLowerCase();
            return hay.includes(searchQuery);
        });
    }
    renderPapers();
}

// ── Data Loading ─────────────────────────────────────────
async function fetchAvailableDates() {
    try {
        const url = DATA_CONFIG.getDataUrl('assets/file-list.txt');
        const resp = await fetch(url);
        if (!resp.ok) return;
        const text = await resp.text();
        const re = /(\d{4}-\d{2}-\d{2})_ai_enhanced\.jsonl/;
        const seen = new Set();
        text.trim().split('\n').forEach(line => {
            const m = line.match(re);
            if (m && !seen.has(m[1])) {
                seen.add(m[1]);
                availableDates.push(m[1]);
            }
        });
        availableDates.sort((a, b) => b.localeCompare(a));
    } catch (e) {
        console.error('Failed to fetch dates:', e);
    }
}

async function loadDate(date) {
    currentDate = date;
    expandedId = null;
    searchQuery = '';
    document.getElementById('searchInput').value = '';
    document.getElementById('dateDisplay').textContent = fmtDate(date);
    document.getElementById('searchBar').classList.add('hidden');

    showLoading();
    try {
        const url = DATA_CONFIG.getDataUrl(`data/${date}_ai_enhanced.jsonl`);
        const resp = await fetch(url);
        if (!resp.ok || resp.status === 404) {
            allPapers = [];
            filteredPapers = [];
            renderPapers();
            return;
        }
        const text = await resp.text();
        allPapers = parseJSONL(text, date);
        filteredPapers = [...allPapers];
        renderPapers();
    } catch (e) {
        console.error('Failed to load papers:', e);
        allPapers = [];
        filteredPapers = [];
        renderPapers();
    }
}

function parseJSONL(text, date) {
    const papers = [];
    text.trim().split('\n').forEach(line => {
        if (!line.trim()) return;
        try {
            const p = JSON.parse(line);
            papers.push({
                id: p.id || '',
                title: p.title || '',
                authors: Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || ''),
                summary: p.summary || '',
                categories: p.categories || [],
                matched: !!p.matched,
                // AI fields (may be nested under 'AI' or flat)
                tldr: (p.AI && p.AI.tldr) || p.tldr || '',
                motivation: (p.AI && p.AI.motivation) || p.motivation || '',
                method: (p.AI && p.AI.method) || p.method || '',
                result: (p.AI && p.AI.result) || p.result || '',
                conclusion: (p.AI && p.AI.conclusion) || p.conclusion || '',
                future_work: (p.AI && p.AI.future_work) || p.future_work || '',
                abs: p.abs || `https://arxiv.org/abs/${p.id}`,
                pdf: p.pdf || `https://arxiv.org/pdf/${p.id}`,
                date: date
            });
        } catch (e) { /* skip malformed lines */ }
    });
    return papers;
}

// ── Rendering ────────────────────────────────────────────
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('papers').innerHTML = '';
    document.getElementById('noPapers').classList.add('hidden');
    document.getElementById('noMatch').classList.add('hidden');
}

function renderPapers() {
    document.getElementById('loading').classList.add('hidden');
    const container = document.getElementById('papers');
    const noPapers = document.getElementById('noPapers');
    const noMatch = document.getElementById('noMatch');

    if (allPapers.length === 0) {
        container.innerHTML = '';
        noPapers.classList.remove('hidden');
        noMatch.classList.add('hidden');
        return;
    }
    noPapers.classList.add('hidden');

    if (filteredPapers.length === 0 && searchQuery) {
        container.innerHTML = '';
        noMatch.classList.remove('hidden');
        return;
    }
    noMatch.classList.add('hidden');

    // Sort: matched first
    const sorted = [...filteredPapers].sort((a, b) => {
        if (a.matched && !b.matched) return -1;
        if (!a.matched && b.matched) return 1;
        return 0;
    });

    let html = '';
    sorted.forEach(p => {
        const dot = p.matched ? '<span class="match-dot"></span>' : '<span class="match-dot" style="visibility:hidden"></span>';
        html += `
        <div class="paper-row" data-id="${esc(p.id)}">
            <div class="paper-row-inner">
                ${dot}
                <span class="paper-id"><a href="https://arxiv.org/abs/${esc(p.id)}" target="_blank" onclick="event.stopPropagation()">${esc(p.id)}</a></span>
                <div class="paper-content">
                    <span class="paper-title" onclick="toggleExpand('${esc(p.id)}')">${esc(p.title)}</span>
                    <div class="paper-authors">${esc(p.authors)}</div>
                </div>
            </div>
            <div class="paper-expand" id="expand-${esc(p.id)}">
                ${renderExpand(p)}
            </div>
        </div>`;
    });
    container.innerHTML = html;

    // Re-expand if one was open before re-render
    if (expandedId) {
        const el = document.getElementById('expand-' + expandedId);
        if (el) el.classList.add('open');
    }

    // KaTeX render
    if (typeof renderMathInElement !== 'undefined') {
        try {
            renderMathInElement(container, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError: false
            });
        } catch(e) {}
    }
}

function renderExpand(p) {
    const fields = [
        ['一句话总结', p.tldr],
        ['动机', p.motivation],
        ['方法', p.method],
        ['结果', p.result],
        ['结论', p.conclusion],
        ['未来工作', p.future_work],
    ];
    let html = '';
    fields.forEach(([label, val]) => {
        if (val) html += `<h4>${label}</h4><p>${esc(val)}</p>`;
    });
    if (p.summary) {
        html += `<div class="expand-abstract"><strong>Abstract</strong><br>${esc(p.summary)}</div>`;
    }
    html += `
        <div class="expand-links">
            <a href="${esc(p.abs)}" target="_blank">arXiv</a>
            <a href="${esc(p.pdf)}" target="_blank">PDF</a>
        </div>`;
    return html;
}

// ── Inline expand/collapse ───────────────────────────────
function toggleExpand(id) {
    const el = document.getElementById('expand-' + id);
    if (!el) return;

    if (expandedId && expandedId !== id) {
        const prev = document.getElementById('expand-' + expandedId);
        if (prev) prev.classList.remove('open');
    }

    el.classList.toggle('open');
    expandedId = el.classList.contains('open') ? id : null;

    // Scroll expanded content into view if opening
    if (expandedId === id) {
        setTimeout(() => {
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 50);
    }

    // KaTeX render in expanded content
    if (el.classList.contains('open') && typeof renderMathInElement !== 'undefined') {
        try {
            renderMathInElement(el, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError: false
            });
        } catch(e) {}
    }
}

// ── Trend Bar ────────────────────────────────────────────
async function fetchTrend() {
    try {
        const url = DATA_CONFIG.getDataUrl('assets/file-list.txt');
        const resp = await fetch(url);
        if (!resp.ok) return;
        const text = await resp.text();
        const re = /(\d{4}-\d{2}-\d{2})_ai_enhanced\.jsonl/;
        const dates = [];
        text.trim().split('\n').forEach(line => {
            const m = line.match(re);
            if (m) dates.push(m[1]);
        });

        // Count papers per date (approximate: count files)
        const counts = {};
        dates.forEach(d => { counts[d] = (counts[d] || 0) + 1; });

        const sorted = Object.keys(counts).sort().slice(-10);
        const maxCount = Math.max(1, ...sorted.map(d => counts[d]));

        const bar = document.getElementById('trendBar');
        let barsHTML = '<div class="trend-bars">';
        sorted.forEach(d => {
            const h = Math.max(4, (counts[d] / maxCount) * 24);
            barsHTML += `<div class="trend-bar-item" title="${d}: ${counts[d]}"><div class="trend-bar-fill" style="height:${h}px"></div></div>`;
        });
        barsHTML += '</div>';
        const total = dates.length;
        bar.innerHTML = `<span>Recent activity</span>${barsHTML}<span>${total} days of data</span>`;
    } catch (e) {
        console.error('Trend fetch failed:', e);
    }
}

// ── Helpers ──────────────────────────────────────────────
function fmtDate(d) {
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function esc(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/"/g, '&quot;');
}

// Close date picker on outside click
document.addEventListener('click', (e) => {
    const popup = document.getElementById('datePicker');
    const btn = document.getElementById('dateBtn');
    if (!popup.classList.contains('hidden') &&
        !popup.contains(e.target) && !btn.contains(e.target)) {
        hideDatePicker();
        flatpickrInstance?.close();
    }
});

// Keyboard: Escape to close search, collapse expanded paper
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (expandedId) {
            const el = document.getElementById('expand-' + expandedId);
            if (el) el.classList.remove('open');
            expandedId = null;
        }
        const bar = document.getElementById('searchBar');
        if (!bar.classList.contains('hidden')) {
            bar.classList.add('hidden');
            document.getElementById('searchInput').value = '';
            searchQuery = '';
            applySearch();
        }
    }
});
