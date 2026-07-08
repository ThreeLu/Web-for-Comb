/**
 * Comb-Search — Frontend
 */

// ── State ────────────────────────────────────────────────
let availableDates = [];
let currentDate = '';
let allPapers = [];
let expandedId = null;
let flatpickrInstance = null;
let searchTerm = '';

// ── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initFlatpickr();
    fetchAvailableDates().then(() => {
        if (availableDates.length > 0) {
            loadDate(availableDates[0]);
        } else {
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('noPapers').classList.remove('hidden');
            document.getElementById('noPapers').textContent = 'Failed to load data. Check back later.';
        }
    }).catch(() => {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('noPapers').classList.remove('hidden');
        document.getElementById('noPapers').textContent = 'Failed to load data. Check back later.';
    });
    fetchTrend();
});

// ── Flatpickr ────────────────────────────────────────────
function initFlatpickr() {
    try {
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
    } catch(e) { console.warn('Flatpickr init failed:', e); }
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
document.getElementById('searchInput').addEventListener('input', (e) => {
    searchTerm = e.target.value.trim().toLowerCase();
    expandedId = null;
    renderPapers();
});

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
    searchTerm = '';
    const si = document.getElementById('searchInput');
    if (si) si.value = '';
    document.getElementById('dateDisplay').textContent = fmtDate(date);

    showLoading();
    try {
        const url = DATA_CONFIG.getDataUrl(`data/${date}_ai_enhanced.jsonl`);
        const resp = await fetch(url);
        if (!resp.ok || resp.status === 404) {
            allPapers = [];
            renderPapers();
            return;
        }
        const text = await resp.text();
        allPapers = parseJSONL(text, date);
        renderPapers();
    } catch (e) {
        console.error('Failed to load papers:', e);
        allPapers = [];
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
                matchKeywords: (p.match_reasons && p.match_reasons.keywords) || [],
                matchAuthors: (p.match_reasons && p.match_reasons.authors) || [],
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

function paperMatchesSearch(p, term) {
    if (!term) return true;
    const hay = [
        p.title, p.authors, p.tldr,
        p.matchKeywords.join(' '), p.matchAuthors.join(' ')
    ].join(' ').toLowerCase();
    return hay.includes(term);
}

// Relevance: a watched author is a stronger signal than a keyword hit, and
// more distinct hits => more relevant. Used to sort the most relevant to top.
function relevanceScore(p) {
    return p.matchKeywords.length + p.matchAuthors.length * 3;
}

// Category color system (D). Each arXiv category maps to a CSS accent var.
const CAT_INFO = {
    'math.CO': { zh: '组合', v: '--cat-co' },
    'math.NT': { zh: '数论', v: '--cat-nt' },
    'math.PR': { zh: '概率', v: '--cat-pr' },
    'math.GR': { zh: '群论', v: '--cat-gr' },
};
function catVar(cat) {
    const info = CAT_INFO[cat];
    return info ? `var(${info.v})` : 'var(--accent)';
}
function catTag(cat) {
    const info = CAT_INFO[cat];
    const zh = info ? info.zh : '';
    return `<span class="cat-tag"><span class="cat-dot"></span>${zh}<span class="cat-code">${esc(cat || '')}</span></span>`;
}

function matchChips(p) {
    const chips = [];
    p.matchAuthors.forEach(a => chips.push(`<span class="match-chip match-chip-author">@${esc(a)}</span>`));
    p.matchKeywords.forEach(k => chips.push(`<span class="match-chip">${esc(k)}</span>`));
    return chips.length ? `<div class="match-chips">${chips.join('')}</div>` : '';
}

// Wrap matched keywords in <mark>, without disturbing $…$ math spans.
function highlightTitle(rawTitle, terms) {
    let text = esc(rawTitle);
    if (!terms || !terms.length) return text;
    const math = [];
    text = text.replace(/\$\$[^$]*\$\$|\$[^$]*\$/g, m => {
        math.push(m);
        return ` ${math.length - 1} `;
    });
    terms.forEach(t => {
        const pat = new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + 's?', 'gi');
        text = text.replace(pat, m => `<mark>${m}</mark>`);
    });
    text = text.replace(/ (\d+) /g, (_, i) => math[+i]);
    return text;
}

function renderPapers() {
    document.getElementById('loading').classList.add('hidden');
    const container = document.getElementById('papers');
    const noPapers = document.getElementById('noPapers');
    const noMatch = document.getElementById('noMatch');
    const summary = document.getElementById('daySummary');
    const searchBar = document.getElementById('searchBar');

    if (allPapers.length === 0) {
        container.innerHTML = '';
        if (summary) summary.classList.add('hidden');
        if (searchBar) searchBar.classList.add('hidden');
        noMatch.classList.add('hidden');
        noPapers.classList.remove('hidden');
        return;
    }
    noPapers.classList.add('hidden');
    if (searchBar) searchBar.classList.remove('hidden');

    const visible = allPapers
        .filter(p => paperMatchesSearch(p, searchTerm))
        .map((p, i) => [p, i])                       // decorate with original index
        .sort((a, b) => relevanceScore(b[0]) - relevanceScore(a[0]) || a[1] - b[1])
        .map(pair => pair[0]);                        // stable: relevance desc, then original order
    if (summary) {
        summary.classList.remove('hidden');
        summary.textContent = searchTerm
            ? `${fmtDate(currentDate)} · ${visible.length}/${allPapers.length} 篇`
            : `${fmtDate(currentDate)} · ${allPapers.length} 篇`;
    }

    if (visible.length === 0) {
        container.innerHTML = '';
        noMatch.classList.remove('hidden');
        return;
    }
    noMatch.classList.add('hidden');

    let html = '';
    visible.forEach((p, i) => {
        const cat = (p.categories && p.categories[0]) || '';
        html += `
        <div class="paper-row" data-id="${esc(p.id)}" style="--cat:${catVar(cat)}">
            <div class="paper-row-inner">
                <span class="paper-num">${i + 1}</span>
                <div class="paper-content">
                    <span class="paper-title" onclick="toggleExpand('${esc(p.id)}')">${highlightTitle(p.title, p.matchKeywords)}</span>
                    <div class="paper-authors">${esc(p.authors)}</div>
                    <div class="paper-meta">
                        ${catTag(cat)}
                        ${(p.matchKeywords.length || p.matchAuthors.length) ? '<span class="meta-sep"></span>' + matchChips(p) : ''}
                    </div>
                </div>
                <a href="https://arxiv.org/abs/${esc(p.id)}" target="_blank" class="arxiv-link" title="Open on arXiv" onclick="event.stopPropagation()">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                </a>
            </div>
            <div class="paper-expand" id="expand-${esc(p.id)}">
                <div class="paper-expand-inner"><div class="expand-card">${renderExpand(p)}</div></div>
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
                throwOnError: false,
                macros: {
                    "\\exstar": "\\mathrm{ex}^*",
                    "\\ex": "\\mathrm{ex}",
                    "\\Ftor": "F_t",
                    "\\Ft": "F_t",
                    "\\Wn": "W_n",
                    "\\Cn": "C_n",
                    "\\E": "\\mathbb{E}",
                    "\\P": "\\mathbb{P}",
                    "\\R": "\\mathbb{R}",
                    "\\N": "\\mathbb{N}",
                    "\\Z": "\\mathbb{Z}",
                    "\\cL": "\\mathcal{L}",
                    "\\cC": "\\mathcal{C}",
                    "\\cB": "\\mathcal{B}",
                    "\\cF": "\\mathcal{F}",
                    "\\cG": "\\mathcal{G}",
                    "\\cH": "\\mathcal{H}",
                    "\\cP": "\\mathcal{P}",
                    "\\cS": "\\mathcal{S}",
                    "\\cT": "\\mathcal{T}",
                    "\\calL": "\\mathcal{L}",
                    "\\calC": "\\mathcal{C}",
                    "\\calF": "\\mathcal{F}",
                    "\\calG": "\\mathcal{G}",
                    "\\calH": "\\mathcal{H}",
                    "\\calP": "\\mathcal{P}",
                }
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
                throwOnError: false,
                macros: {
                    "\\exstar": "\\mathrm{ex}^*",
                    "\\ex": "\\mathrm{ex}",
                    "\\Ftor": "F_t",
                    "\\Ft": "F_t",
                    "\\Wn": "W_n",
                    "\\Cn": "C_n",
                    "\\E": "\\mathbb{E}",
                    "\\P": "\\mathbb{P}",
                    "\\R": "\\mathbb{R}",
                    "\\N": "\\mathbb{N}",
                    "\\Z": "\\mathbb{Z}",
                    "\\cL": "\\mathcal{L}",
                    "\\cC": "\\mathcal{C}",
                    "\\cB": "\\mathcal{B}",
                    "\\cF": "\\mathcal{F}",
                    "\\cG": "\\mathcal{G}",
                    "\\cH": "\\mathcal{H}",
                    "\\cP": "\\mathcal{P}",
                    "\\cS": "\\mathcal{S}",
                    "\\cT": "\\mathcal{T}",
                    "\\calL": "\\mathcal{L}",
                    "\\calC": "\\mathcal{C}",
                    "\\calF": "\\mathcal{F}",
                    "\\calG": "\\mathcal{G}",
                    "\\calH": "\\mathcal{H}",
                    "\\calP": "\\mathcal{P}",
                }
            });
        } catch(e) {}
    }
}

// ── Trend Bar ────────────────────────────────────────────
async function fetchTrend() {
    try {
        const url = DATA_CONFIG.getDataUrl('assets/stats.json');
        const resp = await fetch(url);
        if (!resp.ok) return;
        const stats = await resp.json();
        const daily = (stats.daily || []).slice(-14);   // real matched counts per day
        if (!daily.length) return;

        const maxCount = Math.max(1, ...daily.map(d => d.matched));
        const bar = document.getElementById('trendBar');
        let barsHTML = '<div class="trend-bars">';
        daily.forEach(d => {
            const h = Math.max(3, (d.matched / maxCount) * 24);
            barsHTML += `<div class="trend-bar-item" title="${d.date}: ${d.matched} 篇匹配（共抓 ${d.fetched}）"><div class="trend-bar-fill" style="height:${h}px"></div></div>`;
        });
        barsHTML += '</div>';
        bar.innerHTML =
            `<span>近 ${daily.length} 天匹配</span>${barsHTML}` +
            `<span>共 ${stats.total_matched} 篇 / ${stats.total_days} 天</span>`;
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

// Keyboard: Escape to collapse expanded paper
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && expandedId) {
        const el = document.getElementById('expand-' + expandedId);
        if (el) el.classList.remove('open');
        expandedId = null;
    }
});

// ── Theme toggle + header shadow on scroll ───────────────
(function () {
    const root = document.documentElement;
    const btn = document.getElementById('themeToggle');
    const sun = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
    const moon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

    function isDark() {
        const t = root.getAttribute('data-theme');
        if (t) return t === 'dark';
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    function paint() { if (btn) btn.innerHTML = isDark() ? sun : moon; }

    try {
        const saved = localStorage.getItem('cs-theme');
        if (saved === 'dark' || saved === 'light') root.setAttribute('data-theme', saved);
    } catch (e) { /* private mode */ }
    paint();

    if (btn) btn.addEventListener('click', () => {
        const next = isDark() ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('cs-theme', next); } catch (e) {}
        paint();
    });

    const hdr = document.querySelector('header');
    if (hdr) window.addEventListener('scroll', () => {
        hdr.classList.toggle('scrolled', window.scrollY > 4);
    }, { passive: true });
})();
