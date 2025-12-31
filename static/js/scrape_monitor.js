(function () {
    const runningEl = document.getElementById("monitor-running");
    const startedEl = document.getElementById("monitor-started");
    const updatedEl = document.getElementById("monitor-updated");
    const tableBody = document.getElementById("monitor-table-body");

    if (!runningEl || !startedEl || !updatedEl || !tableBody) {
        return;
    }

    const STATUS_CLASS = {
        OK: "status-ok",
        NEEDS_ATTENTION: "status-needs_attention",
        FAIL: "status-fail",
    };

    const pollIntervalMs = 3000;

    async function loadMonitor() {
        try {
            const payload = await fetch("/scraper-monitor").then((res) => res.json());
            renderSummary(payload);
            renderDealers(payload);
        } catch (err) {
            console.error("Failed to load scraper monitor", err);
        }
    }

    function renderSummary(payload) {
        runningEl.textContent = payload.running ? "Yes" : "No";
        startedEl.textContent = formatDate(payload.started_at);
        updatedEl.textContent = formatDate(payload.updated_at);
    }

    function renderDealers(payload) {
        const dealers = payload.dealers || {};
        const dealerNames = Object.keys(dealers).sort((a, b) => a.localeCompare(b));

        if (!dealerNames.length) {
            tableBody.innerHTML = `<tr class="empty-row"><td colspan="6">Waiting for scrape data…</td></tr>`;
            return;
        }

        tableBody.innerHTML = "";

        dealerNames.forEach((dealerName) => {
            const dealer = dealers[dealerName];
            const row = document.createElement("tr");

            row.appendChild(textCell(dealerName));
            row.appendChild(statusCell(dealer.status));
            row.appendChild(textCell(dealer.total_rows));
            row.appendChild(textCell(dealer.invalid_required_rows));
            row.appendChild(textCell(dealer.attention_rows));
            row.appendChild(textCell(formatIssues(dealer.top_issues)));

            tableBody.appendChild(row);
        });
    }

    function statusCell(status) {
        const td = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `status-badge ${STATUS_CLASS[status] || ""}`;
        badge.textContent = status || "—";
        td.appendChild(badge);
        return td;
    }

    function textCell(value) {
        const td = document.createElement("td");
        td.textContent = value ?? "—";
        return td;
    }

    function formatIssues(issues) {
        if (!Array.isArray(issues) || issues.length === 0) return "—";
        return issues.slice(0, 3).join(", ");
    }

    function formatDate(isoString) {
        if (!isoString) return "—";
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) return "—";
        return date.toLocaleString();
    }

    loadMonitor();
    setInterval(loadMonitor, pollIntervalMs);
})();