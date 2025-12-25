(async function () {
    // ---------------- START BACKGROUND SCRAPING ----------------
    fetch("/start-scraping");

    const progressEl = document.getElementById("progress");
    const listEl = document.getElementById("specials-list");

    let lastRowCount = 0;

    const poll = setInterval(async () => {
        const status = await fetch("/scrape-status").then(r => r.json());
        const rows = await fetch("/scrape-results").then(r => r.json());

        progressEl.textContent = `${status.progress} / ${status.total}`;


        if (rows.length > lastRowCount) {
            renderGrouped(rows);
            lastRowCount = rows.length;
        }

        if (!status.running) {
            clearInterval(poll);
            progressEl.textContent = `Loaded ${rows.length} rows`;
        }
    }, 1000);

    function renderGrouped(rows) {
        if (!listEl) return;

        listEl.innerHTML = "";

        const grouped = rows.reduce((acc, row) => {
            const dealership = row.Dealership || "Unknown Dealership";
            if (!acc.has(dealership)) {
                acc.set(dealership, []);
            }
            acc.get(dealership).push(row);
            return acc;
        }, new Map());

        const columnOrder = [
            "Due at Signing ($)",
            "Expires",
            "MSRP ($)",
            "Model",
            "Monthly ($)",
            "Term (months)",
        ];

        grouped.forEach((offers, dealership) => {
            const section = document.createElement("section");
            section.className = "dealership-section";

            const header = document.createElement("div");
            header.className = "dealership-header";

            const title = document.createElement("h2");

            const commonLink = findDealershipLink(offers);
            if (commonLink) {
                const anchor = document.createElement("a");
                anchor.href = commonLink;
                anchor.target = "_blank";
                anchor.rel = "noopener";
                anchor.textContent = dealership;
                title.appendChild(anchor);
            } else {
                title.textContent = dealership;
            }
            header.appendChild(title);

            const count = document.createElement("span");
            count.className = "dealership-count";
            count.textContent = `${offers.length} offer${offers.length === 1 ? "" : "s"}`;
            header.appendChild(count);

            section.appendChild(header);

            const table = document.createElement("table");
            table.className = "dealership-table";

            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");
            columnOrder.forEach((label) => {
                const th = document.createElement("th");
                th.scope = "col";
                th.textContent = label;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");
            offers.forEach((offer) => {
                const rowEl = document.createElement("tr");
                columnOrder.forEach((key) => {
                    const td = document.createElement("td");
                    const value = offer[key];

                    if (typeof value === "string" && value.startsWith("http")) {
                        const link = document.createElement("a");
                        link.href = value;
                        link.target = "_blank";
                        link.rel = "noopener";
                        link.textContent = value;
                        td.appendChild(link);
                    } else {
                        td.textContent = value ?? "";
                    }

                    rowEl.appendChild(td);
                });
                tbody.appendChild(rowEl);
            });

            table.appendChild(tbody);
            section.appendChild(table);
            listEl.appendChild(section);
        });
    }

    function findDealershipLink(offers) {
        for (const offer of offers) {
            const linkEntry = Object.entries(offer).find(([key, value]) => {
                if (key === "Dealership") return false;
                return typeof value === "string" && value.startsWith("http");
            });

            if (linkEntry) {
                return linkEntry[1];
            }
        }

        return null;

    }

    // ---------------- MANUAL OFFERS MODAL ----------------
    const openBtn = document.getElementById("open-manual-offers");
    const modal = document.getElementById("manual-offers-modal");

    if (openBtn && modal) {
        const cancelBtn = document.getElementById("cancel-manual-offer");
        const continueBtn = document.getElementById("continue-manual-offer");
        const linkInput = document.getElementById("manual-offer-link");
        const dealershipInput = document.getElementById("manual-dealership-name");

        openBtn.addEventListener("click", () => {
            modal.classList.add("is-open");
        });

        cancelBtn.addEventListener("click", () => {
            modal.classList.remove("is-open");
        });

        continueBtn.addEventListener("click", () => {
            const link = linkInput?.value.trim();
            const dealership = dealershipInput?.value.trim();

            const url = new URL("/manual-offers", window.location.origin);
            if (link) url.searchParams.set("offer_link", link);
            if (dealership) url.searchParams.set("dealership", dealership);

            window.open(url.toString(), "_blank", "noopener");
            modal.classList.remove("is-open");
        });
    }
})();
