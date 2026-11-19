EV ADOPTION PREDICTOR
=====================

This version uses:

FRONTEND
--------
- HTML
- CSS
- JavaScript

BACKEND
-------
- Python
- pandas
- scikit-learn
- Matplotlib

No Flask, Django, React, Bootstrap, Chart.js, or other web framework
is required.

FILES
-----
app.py
    Python backend, dataset processing, Matplotlib chart generation,
    chart download, and Linear Regression prediction.

index.html
    GUI structure.

style.css
    GUI design.

script.js
    GUI interaction and communication with the Python backend.


HOW TO RUN
----------
1. Open this folder in VS Code.

2. Install the required packages:

       pip install pandas scikit-learn matplotlib

3. Run:

       py app.py

4. Open:

       http://localhost:8000


PROJECT FLOW
------------
1. Python downloads the same CSV dataset used in the original project.

2. The GUI receives the country list from Python.

3. The user selects a country.

4. Clicking "View Data" requests the selected country's data.

5. Python filters the country data and generates the EV adoption chart
   using Matplotlib.

6. The Matplotlib PNG chart is sent to the browser and displayed.

7. Clicking "Download Chart" calls the Python /api/download-chart
   endpoint.

8. Python generates the selected country's chart and sends it as a
   downloadable PNG file.


PREDICTION LOGIC
----------------
EV Stock Prediction and EV Sales Prediction remain in Python.

The original LinearRegression approach is retained.

For EV Stock:
    target_column = "ev_stock"

For EV Sales:
    target_column = "ev_sales"

If the requested year already exists in the CSV:
    Result Type = Actual Data (CSV)

If the requested year is after the latest available year:
    Python trains LinearRegression using historical year/value data
    and predicts the requested future year.

If the requested year is before the available historical data:
    An error message is returned.

The browser does NOT perform the prediction.

The browser also does NOT generate the chart.

Python handles both prediction and chart generation.


CHART GENERATION
----------------
The chart is generated with Matplotlib in app.py.

The main chart code is:

    plt.figure(figsize=(10, 5))
    plt.plot(
        country_data["year"],
        country_data["ev_stock"],
        marker="o",
        linewidth=2
    )
    plt.title("EV Adoption in " + country)
    plt.xlabel("Year")
    plt.ylabel("Number of Electric Cars")
    plt.xticks(country_data["year"], rotation=45)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

The chart is then saved into an in-memory PNG using BytesIO and
returned by the Python server.

This means the chart generation is clearly handled by Python/Matplotlib.


CHART DOWNLOAD
--------------
The "Download Chart" button calls:

    /api/download-chart

Python generates the chart and returns it with a download filename such as:

    India_EV_Adoption_Chart.png

Therefore both chart generation and chart downloading are handled
through the Python backend.
