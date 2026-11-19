const countrySelect = document.getElementById("country");
const viewBtn = document.getElementById("viewBtn");
const predictBtn = document.getElementById("predictBtn");
const downloadBtn = document.getElementById("downloadBtn");
const predictionType = document.getElementById("predictionType");
const futureYear = document.getElementById("futureYear");
const chartSection = document.getElementById("chartSection");
const chartTitle = document.getElementById("chartTitle");
const latestValue = document.getElementById("latestValue");
const chartImage = document.getElementById("chartImage");
const chartLoader = document.getElementById("chartLoader");
const countryCount = document.getElementById("countryCount");
const result = document.getElementById("result");
const message = document.getElementById("message");
let currentChartUrl = null;

async function loadCountries() {
    countrySelect.disabled = true;
    try {
        const response = await fetch("/api/countries");
        if (!response.ok) throw new Error("Country list request failed");
        const data = await response.json();
        countrySelect.innerHTML = '<option value="">Select a country</option>';
        data.countries.forEach(country => {
            const option = document.createElement("option");
            option.value = country;
            option.textContent = country;
            countrySelect.appendChild(option);
        });
        countryCount.textContent = data.countries.length.toLocaleString();
    } catch (error) {
        showMessage("Could not load countries. Check that the Python server is running and the dataset is available.");
        countrySelect.innerHTML = '<option value="">Countries unavailable</option>';
    } finally {
        countrySelect.disabled = false;
    }
}

function setButtonLoading(button, loading, loadingText, normalText) {
    button.disabled = loading;
    const label = button.querySelector("span:first-child");
    if (label) label.textContent = loading ? loadingText : normalText;
}

viewBtn.addEventListener("click", async () => {
    const country = countrySelect.value;
    if (!country) return showMessage("Please select a country first.");
    hideMessage();
    setButtonLoading(viewBtn, true, "Loading chart...", "View adoption chart");
    chartLoader.classList.remove("hidden");
    chartSection.classList.remove("hidden");
    downloadBtn.disabled = true;

    try {
        const query = encodeURIComponent(country);
        const [dataResponse, chartResponse] = await Promise.all([
            fetch(`/api/data?country=${query}`),
            fetch(`/api/chart?country=${query}`)
        ]);
        const data = await dataResponse.json();
        if (!dataResponse.ok || data.error) throw new Error(data.error || "Could not load country data.");
        if (!chartResponse.ok) {
            const chartError = await chartResponse.json();
            throw new Error(chartError.error || "Could not generate chart.");
        }

        const chartBlob = await chartResponse.blob();
        if (currentChartUrl) URL.revokeObjectURL(currentChartUrl);
        currentChartUrl = URL.createObjectURL(chartBlob);
        chartImage.src = currentChartUrl;
        chartTitle.textContent = `EV Adoption in ${country}`;

        const validRows = data.data.filter(row => row.ev_stock !== null && row.ev_stock !== undefined);
        if (validRows.length) {
            const latest = validRows[validRows.length - 1];
            latestValue.textContent = `Latest: ${Math.round(latest.ev_stock).toLocaleString()} EVs · ${latest.year}`;
        } else {
            latestValue.textContent = "No stock data available";
        }
        downloadBtn.disabled = false;
        chartSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        showMessage(error.message || "Unable to load country data.");
        if (!chartImage.src) chartSection.classList.add("hidden");
    } finally {
        chartLoader.classList.add("hidden");
        setButtonLoading(viewBtn, false, "Loading chart...", "View adoption chart");
    }
});

// Download is served by Python, which creates the Matplotlib PNG.
downloadBtn.addEventListener("click", () => {
    const country = countrySelect.value;
    if (!country) return showMessage("Please select a country first.");
    const link = document.createElement("a");
    link.href = `/api/download-chart?country=${encodeURIComponent(country)}`;
    link.download = `${country.replace(/[^a-z0-9]+/gi, "_")}_EV_Adoption_Chart.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
});

predictBtn.addEventListener("click", async () => {
    const country = countrySelect.value;
    const type = predictionType.value;
    const year = futureYear.value.trim();
    if (!country) return showMessage("Please select a country first.");
    if (!year || !Number.isInteger(Number(year))) return showMessage("Please enter a valid year.");
    if (Number(year) < 1900 || Number(year) > 2200) return showMessage("Please enter a year between 1900 and 2200.");

    hideMessage();
    setButtonLoading(predictBtn, true, "Calculating...", "Generate prediction");
    result.classList.add("hidden");
    try {
        const url = `/api/predict?country=${encodeURIComponent(country)}&type=${encodeURIComponent(type)}&year=${encodeURIComponent(year)}`;
        const response = await fetch(url);
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || "Prediction could not be generated.");

        const formattedValue = Number(data.predicted_value).toLocaleString();
        result.innerHTML = `
            <div class="result-top">
                <div class="result-info">${escapeHTML(data.country)} · ${data.year}</div>
                <span class="result-type">${escapeHTML(data.result_type)}</span>
            </div>
            <div class="result-main">${formattedValue}</div>
            <div class="result-caption">${escapeHTML(data.prediction_name)} · Estimated number of vehicles</div>
        `;
        result.classList.remove("hidden");
        result.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
        showMessage(error.message || "Unable to calculate prediction.");
    } finally {
        setButtonLoading(predictBtn, false, "Calculating...", "Generate prediction");
    }
});

// Quick year chips fill the prediction year field.
document.querySelectorAll(".year-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        futureYear.value = chip.dataset.year;
        document.querySelectorAll(".year-chip").forEach(item => item.classList.remove("active"));
        chip.classList.add("active");
        futureYear.focus();
    });
});

futureYear.addEventListener("input", () => {
    document.querySelectorAll(".year-chip").forEach(chip => {
        chip.classList.toggle("active", chip.dataset.year === futureYear.value);
    });
});

countrySelect.addEventListener("change", () => {
    result.classList.add("hidden");
    hideMessage();
});

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    })[character]);
}

function showMessage(text) {
    message.textContent = text;
    message.classList.remove("hidden");
}
function hideMessage() {
    message.classList.add("hidden");
}

loadCountries();
