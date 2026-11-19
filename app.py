import pandas as pd
import json
import io
import os
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# -----------------------------
# DATASET
# -----------------------------
data = pd.read_csv("aidb-electric-cars-in-use-by-country.csv")

data["year"] = pd.to_numeric(data["year"], errors="coerce")
data["ev_stock"] = pd.to_numeric(data["ev_stock"], errors="coerce")

if "ev_sales" in data.columns:
    data["ev_sales"] = pd.to_numeric(data["ev_sales"], errors="coerce")

countries = sorted(data["country_name"].dropna().unique())

# Optional: keep the original project's graph folder.
os.makedirs("EV_Graphs", exist_ok=True)


# -----------------------------
# COUNTRY DATA
# -----------------------------
def get_country_data(country):
    country_data = data[data["country_name"] == country].copy()
    country_data = country_data.sort_values("year")
    country_data = country_data.dropna(subset=["year"])

    result = []

    for _, row in country_data.iterrows():
        item = {"year": int(row["year"])}

        item["ev_stock"] = (
            float(row["ev_stock"])
            if pd.notna(row["ev_stock"])
            else None
        )

        if "ev_sales" in data.columns:
            item["ev_sales"] = (
                float(row["ev_sales"])
                if pd.notna(row["ev_sales"])
                else None
            )
        else:
            item["ev_sales"] = None

        result.append(item)

    return result


# -----------------------------
# PYTHON / MATPLOTLIB CHART
# -----------------------------
def generate_country_chart(country):
    country_data = data[data["country_name"] == country].copy()
    country_data = country_data.sort_values("year")
    country_data = country_data.dropna(subset=["year", "ev_stock"])

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

    image_buffer = io.BytesIO()
    plt.savefig(image_buffer, format="png", dpi=150)
    plt.close()

    image_buffer.seek(0)
    return image_buffer.getvalue()


# -----------------------------
# ORIGINAL PREDICTION LOGIC
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
        return {
            "error":
            "The dataset does not contain " + target_column + " column."
        }

    country_data = data[data["country_name"] == country].copy()

    country_data = country_data.dropna(
        subset=["year", target_column]
    )

    country_data = country_data.sort_values("year")

    if len(country_data) < 2:
        return {
            "error": "Not enough historical data for prediction!"
        }

    future_year = int(future_year)

    # Same logic as the original project.
    year_data = country_data[
        country_data["year"] == future_year
    ]

    if not year_data.empty:

        predicted_value = year_data[target_column].iloc[0]
        result_type = "Actual Data (CSV)"

    elif future_year > country_data["year"].max():

        X = country_data[["year"]]
        y = country_data[target_column]

        model = LinearRegression()
        model.fit(X, y)

        prediction = model.predict(
            pd.DataFrame({"year": [future_year]})
        )

        predicted_value = max(0, float(prediction[0]))
        result_type = "Future Prediction"

    else:

        return {
            "error":
            "Year is before available historical data."
        }

    return {
        "country": country,
        "year": future_year,
        "result_type": result_type,
        "prediction_name": prediction_name,
        "predicted_value": round(float(predicted_value))
    }


# -----------------------------
# SIMPLE PYTHON WEB SERVER
# -----------------------------
class EVHandler(SimpleHTTPRequestHandler):

    def send_json(self, payload, status=200):

        response = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json"
        )
        self.send_header(
            "Content-Length",
            str(len(response))
        )
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )
        self.end_headers()

        self.wfile.write(response)

    def send_chart(self, country, download=False):

        image_data = generate_country_chart(country)

        if image_data is None:
            self.send_json(
                {
                    "error":
                    "No EV stock data is available for this country."
                },
                400
            )
            return

        filename = (
            country.replace(" ", "_")
            + "_EV_Adoption_Chart.png"
        )

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "image/png"
        )

        if download:
            self.send_header(
                "Content-Disposition",
                'attachment; filename="' + filename + '"'
            )

        self.send_header(
            "Content-Length",
            str(len(image_data))
        )
        self.end_headers()

        self.wfile.write(image_data)

    def do_GET(self):

        parsed = urlparse(self.path)

        path = parsed.path
        query = parse_qs(parsed.query)

        # Countries
        if path == "/api/countries":

            self.send_json(
                {
                    "countries": countries
                }
            )
            return

        # Country data
        if path == "/api/data":

            country = query.get(
                "country",
                [None]
            )[0]

            if (
                not country
                or country not in countries
            ):
                self.send_json(
                    {
                        "error":
                        "Invalid country."
                    },
                    400
                )
                return

            self.send_json(
                {
                    "country": country,
                    "data": get_country_data(country)
                }
            )
            return

        # Python-generated chart for display
        if path == "/api/chart":

            country = query.get(
                "country",
                [None]
            )[0]

            if (
                not country
                or country not in countries
            ):
                self.send_json(
                    {
                        "error":
                        "Invalid country."
                    },
                    400
                )
                return

            self.send_chart(
                country,
                download=False
            )
            return

        # Python-generated downloadable chart
        if path == "/api/download-chart":

            country = query.get(
                "country",
                [None]
            )[0]

            if (
                not country
                or country not in countries
            ):
                self.send_json(
                    {
                        "error":
                        "Invalid country."
                    },
                    400
                )
                return

            self.send_chart(
                country,
                download=True
            )
            return

        # Prediction
        if path == "/api/predict":

            country = query.get(
                "country",
                [None]
            )[0]

            prediction_type = query.get(
                "type",
                [None]
            )[0]

            year = query.get(
                "year",
                [None]
            )[0]

            if (
                not country
                or country not in countries
            ):
                self.send_json(
                    {
                        "error":
                        "Invalid country."
                    },
                    400
                )
                return

            try:
                year = int(year)

            except (TypeError, ValueError):

                self.send_json(
                    {
                        "error":
                        "Please enter a valid year."
                    },
                    400
                )
                return

            result = predict(
                country,
                prediction_type,
                year
            )

            if "error" in result:

                self.send_json(
                    result,
                    400
                )

            else:

                self.send_json(
                    result
                )

            return

        # Serve frontend files
        super().do_GET()


if __name__ == "__main__":

    print("Loading EV dataset...")
    print(
        "Countries available:",
        len(countries)
    )

    print(
        "Open http://localhost:8000 "
        "in your browser."
    )

    server = ThreadingHTTPServer(
        ("localhost", 8000),
        EVHandler
    )

    server.serve_forever()
