// ...new file...
(function () {
    const BASE = (window.API_BASE_URL || window.location.origin).replace(/\/+$/, "");
    window.apiFetch = function (path, opts) {
        // If path is absolute, use it; otherwise prefix with BASE
        const url = /^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(path) ? path : `${BASE}/${path.replace(/^\/+/, "")}`;
        return fetch(url, opts);
    };
})();