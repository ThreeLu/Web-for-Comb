/**
 * Data Source Configuration — Comb-Search
 *
 * Uses relative paths served by GitHub Pages (same domain, no CORS).
 * Falls back to raw.githubusercontent.com for local development.
 */

const DATA_CONFIG = {
    getDataUrl: function(filePath) {
        // Use relative path — GitHub Pages serves everything from the repo root
        return filePath;
    }
};
