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
    const removeButton = document.getElementById("manual-remove-rows");
    const saveButton = document.getElementById("manual-save");
    const cancelButton = document.getElementById("manual-cancel");
    const dataframeBody = document.querySelector("#manual-dataframe tbody");

    const clearInputs = () => {
        columns.forEach(({ id }) => {
            const input = document.getElementById(id);
            if (input) input.value = "";
        });
    };

    const collectRow = () => {
        const row = {};
        columns.forEach(({ id }) => {
            const value = document.getElementById(id)?.value.trim();
            row[id] = value === "" ? "None" : value;
        });
        return row;
    };

    const renderDataframe = () => {
        dataframeBody.innerHTML = "";

        if (rows.length === 0) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = columns.length + 1;
            td.textContent = "No manual offers added yet.";
            td.classList.add("empty-state");
            tr.appendChild(td);
            dataframeBody.appendChild(tr);
            return;
        }

        rows.forEach((row, index) => {
            const tr = document.createElement("tr");

            // checkbox cell
            const selectTd = document.createElement("td");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.dataset.index = index;
            selectTd.appendChild(checkbox);
            tr.appendChild(selectTd);

            // data cells
            columns.forEach(({ id }) => {
                const td = document.createElement("td");
                td.textContent = row[id];
                tr.appendChild(td);
            });

            dataframeBody.appendChild(tr);
        });
    };

    addButton?.addEventListener("click", () => {
        rows.push(collectRow());
        renderDataframe();
        clearInputs();
        document.getElementById(columns[0].id)?.focus();
    });

    removeButton?.addEventListener("click", () => {
        const checked = dataframeBody.querySelectorAll(
            'input[type="checkbox"]:checked'
        );

        if (checked.length === 0) {
            alert("Select at least one row to remove.");
            return;
        }

        const indexes = Array.from(checked)
            .map(cb => Number(cb.dataset.index))
            .sort((a, b) => b - a); // reverse order

        indexes.forEach(i => rows.splice(i, 1));

        renderDataframe();
    });

    saveButton?.addEventListener("click", () => {
        const payload = rows.map(row =>
            columns.reduce((acc, { id, label }) => {
                acc[label] = row[id];
                return acc;
            }, {})
        );

        console.table(payload);
        alert("Manual offers saved locally. Hook API when ready.");
    });

    cancelButton?.addEventListener("click", () => {
        window.close();
    });

    renderDataframe();
})();
