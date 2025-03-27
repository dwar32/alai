from flask import Flask, request, jsonify
import re
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

def get_sheet_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/gpt-key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1_jgw8skMLI1RH9NM051M0Lqp464QzjN5LWnlR5HgqbM").sheet1
    return pd.DataFrame(sheet.get_all_records(head=2))

def extract_article(text):
    match = re.search(r"\b[A-ZА-Я0-9\-]{4,}\b", text)
    return match.group(0) if match else None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", "")
    article = extract_article(message)

    if not article:
        return jsonify({"response": "Не удалось распознать артикул.", "status": "ok"})

    df = get_sheet_data()
    match = df[df["Артикул"].astype(str).str.lower() == article.lower()]

    if not match.empty:
        sizes = match.iloc[0][["19", "20", "21", "22", "23", "24", "25"]]
        available_sizes = [size for size in sizes.index if sizes[size]]
        if available_sizes:
            return jsonify({
                "response": f"Товар {article} есть в наличии. Размеры: {', '.join(available_sizes)}",
                "status": "ok"
            })
        else:
            return jsonify({"response": f"Товар {article} найден, но все размеры распроданы.", "status": "ok"})

    return jsonify({"response": "Артикул не найден в базе.", "status": "ok"})

@app.route("/", methods=["GET"])
def index():
    return "Бот активен"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
