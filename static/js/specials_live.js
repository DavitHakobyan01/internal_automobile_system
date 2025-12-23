(async function () {
    // ---------------- START BACKGROUND SCRAPING ----------------
    fetch("/start-scraping");

    const progressEl = document.getElementById("progress");
    const headEl = document.getElementById("table-head");
    const bodyEl = document.getElementById("table-body");

    let lastRowCount = 0;
    let headerRendered = false;

    const poll = setInterval(async () => {
        const status = await fetch("/scrape-status").then(r => r.json());
        const rows = await fetch("/scrape-results").then(r => r.json());

        progressEl.textContent = `${status.progress} / ${status.total}`;

        // Render header once
        if (rows.length && !headerRendered) {
            renderHeader(rows[0]);
            headerRendered = true;
        }

        // Append only new rows
        if (rows.length > lastRowCount) {
            appendRows(rows.slice(lastRowCount));
            lastRowCount = rows.length;
        }

        if (!status.running) {
            clearInterval(poll);
            progressEl.textContent = `Loaded ${rows.length} rows`;
        }
    }, 1000);

    function renderHeader(sampleRow) {
        headEl.innerHTML = "";
        const tr = document.createElement("tr");
        Object.keys(sampleRow).forEach(key => {
            const th = document.createElement("th");
            th.textContent = key;
            tr.appendChild(th);
        });
        headEl.appendChild(tr);
    }

    function appendRows(rows) {
        rows.forEach(row => {
            const tr = document.createElement("tr");
            Object.values(row).forEach(val => {
                const td = document.createElement("td");
                td.textContent = val ?? "";
                tr.appendChild(td);
            });
            bodyEl.appendChild(tr);
        });
    }

    // ---------------- MANUAL OFFERS MODAL ----------------
    const openBtn = document.getElementById("open-manual-offers");
    const modal = document.getElementById("manual-offers-modal");

    if (openBtn && modal) {
        const cancelBtn = document.getElementById("cancel-manual-offer");
        const continueBtn = document.getElementById("continue-manual-offer");

        openBtn.addEventListener("click", () => {
            modal.classList.add("is-open");
        });

        cancelBtn.addEventListener("click", () => {
            modal.classList.remove("is-open");
        });

        continueBtn.addEventListener("click", () => {
            const link = document
                .getElementById("manual-offer-link")
                .value
                .trim();

            const url = new URL("/manual-offers", window.location.origin);
            if (link) url.searchParams.set("offer_link", link);

            window.open(url.toString(), "_blank", "noopener");
            modal.classList.remove("is-open");
        });
    }
})();
