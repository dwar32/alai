from flask import Flask, request, jsonify
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Подключение к Google Sheets
def get_sheet_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gpt-key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Остатки_бот").sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

@app.route("/webhook", methods=["POST"])
def check_stock():
    data = request.json
    message = data.get("message", "").lower()

    df = get_sheet_data()

    for _, row in df.iterrows():
        if str(row["Артикул"]).lower() in message:
            return jsonify({
                "status": "ok",
                "response": f'Товар с артикулом {row["Артикул"]}: в наличии {row["Остаток"]}'
            })

    return jsonify({"status": "ok", "response": "Не удалось найти артикул в базе."})

@app.route("/", methods=["GET"])
def index():
    return "Бот работает"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
