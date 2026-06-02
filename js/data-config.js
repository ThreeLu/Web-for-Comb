/**
 * Data Source Configuration — Comb-Search
 */

const DATA_CONFIG = {
    repoOwner: 'ThreeLu',
    repoName: 'Web-for-Comb',
    dataBranch: 'main',

    getDataBaseUrl: function() {
        return `https://raw.githubusercontent.com/${this.repoOwner}/${this.repoName}/${this.dataBranch}`;
    },

    getDataUrl: function(filePath) {
        return `${this.getDataBaseUrl()}/${filePath}`;
    }
};
