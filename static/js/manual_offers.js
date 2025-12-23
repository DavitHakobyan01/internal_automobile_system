(() => {
    const columns = [
        { id: "manual-model", label: "Model" },
        { id: "manual-monthly", label: "Monthly ($)" },
        { id: "manual-term", label: "Term (months)" },
        { id: "manual-due", label: "Due at Signing ($)" },
        { id: "manual-msrp", label: "MSRP ($)" },
        { id: "manual-apr", label: "APR (%)" },
        { id: "manual-expires", label: "Expires" }
    ];

    const rows = [];
    const addButton = document.getElementById("manual-add-row");
    const saveButton = document.getElementById("manual-save");
    const cancelButton = document.getElementById("manual-cancel");
    const dataframeBody = document.querySelector("#manual-dataframe tbody");

    const clearInputs = () => {
        columns.forEach(({ id }) => {
            const input = document.getElementById(id);
            if (input) {
                input.value = "";
            }
        });
    };

    const renderDataframe = () => {
        dataframeBody.innerHTML = "";

        if (rows.length === 0) {
            const emptyRow = document.createElement("tr");
            const emptyCell = document.createElement("td");
            emptyCell.colSpan = columns.length;
            emptyCell.textContent = "No manual offers added yet.";
            emptyCell.classList.add("empty-state");
            emptyRow.appendChild(emptyCell);
            dataframeBody.appendChild(emptyRow);
            return;
        }

        rows.forEach((row) => {
            const tr = document.createElement("tr");
            columns.forEach(({ id }) => {
                const td = document.createElement("td");
                td.textContent = row[id];
                tr.appendChild(td);
            });
            dataframeBody.appendChild(tr);
        });
    };

    const collectRow = () => {
        const row = {};
        columns.forEach(({ id }) => {
            const value = document.getElementById(id)?.value.trim() || "";
            row[id] = value === "" ? "None" : value;
        });
        return row;
    };

    addButton?.addEventListener("click", () => {
        rows.push(collectRow());
        renderDataframe();
        clearInputs();
        document.getElementById(columns[0].id)?.focus();
    });

    saveButton?.addEventListener("click", () => {
        const payload = rows.map((row) =>
            columns.reduce((acc, { id, label }) => {
                acc[label] = row[id];
                return acc;
            }, {})
        );
        console.table(payload);
        alert("Manual offers saved locally. Hook this up to your API when ready.");
    });

    cancelButton?.addEventListener("click", () => {
        window.close();
    });

    renderDataframe();
})();