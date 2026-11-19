import pandas as pd
import json
import io
import os
from flask import Flask, request, jsonify, send_file
from sklearn.linear_model import LinearRegression
import matplotlib
matplotlib.use("Agg")  # Non-GUI backend required for serverless
import matplotlib.pyplot as plt

app = Flask(__name__)

# Load dataset — CSV lives in project root, one level above api/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "aidb-electric-cars-in-use-by-country.csv")

data = pd.read_csv(CSV_PATH)
data["year"] = pd.to_numeric(data["year"], errors="coerce")
data["ev_stock"] = pd.to_numeric(data["ev_stock"], errors="coerce")
if "ev_sales" in data.columns:
    data["ev_sales"] = pd.to_numeric(data["ev_sales"], errors="coerce")

countries = sorted(data["country_name"].dropna().unique())


# -----------------------------
# COUNTRY DATA
# -----------------------------
def get_country_data(country):
    country_data = data[data["country_name"] == country].copy()
    country_data = country_data.sort_values("year").dropna(subset=["year"])
    result = []
    for _, row in country_data.iterrows():
        item = {"year": int(row["year"])}
        item["ev_stock"] = float(row["ev_stock"]) if pd.notna(row["ev_stock"]) else None
        item["ev_sales"] = (
            float(row["ev_sales"])
            if "ev_sales" in data.columns and pd.notna(row["ev_sales"])
            else None
        )
        result.append(item)
    return result


# -----------------------------
# MATPLOTLIB CHART
# -----------------------------
def generate_country_chart(country):
    country_data = data[data["country_name"] == country].copy()
    country_data = country_data.sort_values("year").dropna(subset=["year", "ev_stock"])
    if country_data.empty:
        return None
    plt.figure(figsize=(10, 5))
    plt.plot(
        country_data["year"],
        country_data["ev_stock"],
        marker="o",
        linewidth=2
    )
    plt.title("EV Adoption in " + country, fontsize=14)
    plt.xlabel("Year")
    plt.ylabel("Number of Electric Cars")
    plt.xticks(country_data["year"], rotation=45)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return buf


# -----------------------------
# PREDICTION LOGIC
# -----------------------------
def predict(country, prediction_type, future_year):
    if prediction_type == "stock":
        target_column = "ev_stock"
        prediction_name = "EV Stock"
    elif prediction_type == "sales":
        target_column = "ev_sales"
        prediction_name = "EV Sales"
    else:
        return {"error": "Invalid prediction type."}

    if target_column not in data.columns:
        return {"error": "The dataset does not contain " + target_column + " column."}

    country_data = data[data["country_name"] == country].copy()
    country_data = country_data.dropna(subset=["year", target_column]).sort_values("year")

    if len(country_data) < 2:
        return {"error": "Not enough historical data for prediction!"}

    future_year = int(future_year)
    year_data = country_data[country_data["year"] == future_year]

    if not year_data.empty:
        predicted_value = year_data[target_column].iloc[0]
        result_type = "Actual Data (CSV)"
    elif future_year > country_data["year"].max():
        X = country_data[["year"]]
        y = country_data[target_column]
        model = LinearRegression()
        model.fit(X, y)
        predicted_value = max(0, float(model.predict(pd.DataFrame({"year": [future_year]}))[0]))
        result_type = "Future Prediction"
    else:
        return {"error": "Year is before available historical data."}

    return {
        "country": country,
        "year": future_year,
        "result_type": result_type,
        "prediction_name": prediction_name,
        "predicted_value": round(float(predicted_value))
    }


# -----------------------------
# FLASK ROUTES
# -----------------------------
@app.route("/api/countries")
def api_countries():
    return jsonify({"countries": list(countries)})


@app.route("/api/data")
def api_data():
    country = request.args.get("country")
    if not country or country not in countries:
        return jsonify({"error": "Invalid country."}), 400
    return jsonify({"country": country, "data": get_country_data(country)})


@app.route("/api/chart")
def api_chart():
    country = request.args.get("country")
    if not country or country not in countries:
        return jsonify({"error": "Invalid country."}), 400
    buf = generate_country_chart(country)
    if buf is None:
        return jsonify({"error": "No EV stock data available for this country."}), 400
    return send_file(buf, mimetype="image/png")


@app.route("/api/download-chart")
def api_download_chart():
    country = request.args.get("country")
    if not country or country not in countries:
        return jsonify({"error": "Invalid country."}), 400
    buf = generate_country_chart(country)
    if buf is None:
        return jsonify({"error": "No EV stock data available for this country."}), 400
    filename = country.replace(" ", "_") + "_EV_Adoption_Chart.png"
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name=filename)


@app.route("/api/predict")
def api_predict():
    country = request.args.get("country")
    prediction_type = request.args.get("type")
    year = request.args.get("year")

    if not country or country not in countries:
        return jsonify({"error": "Invalid country."}), 400
    try:
        year = int(year)
    except (TypeError, ValueError):
        return jsonify({"error": "Please enter a valid year."}), 400

    result = predict(country, prediction_type, year)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)
