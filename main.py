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
    data = sheet.get_all_records(head=1)  
    return pd.DataFrame(data)

def extract_article(text):
    match = re.search(r"\b[A-ZА-Я0-9\-]{4,}\b", text)
    return match.group(0) if match else None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # 👇 Логируем всё, что прислал SMMBOT
    print("🔥 Полученные данные от SMMBOT:", data)

    # Временно отключим логику, просто вернем тестовый ответ
    return jsonify({"response": "Получено!", "status": "ok"})


    if not article:
        return jsonify({"response": "Не удалось распознать артикул.", "status": "ok"})

    df = get_sheet_data()

    if "Артикул" not in df.columns:
        return jsonify({"response": "Ошибка: колонка 'Артикул' не найдена в таблице.", "status": "error"})

    match = df[df["Артикул"].astype(str).str.lower() == article.lower()]

    if not match.empty:
        size_columns = [str(i) for i in range(19, 42)] + ["56"]
        size_columns = [col for col in size_columns if col in df.columns]  
        sizes = match.iloc[0][size_columns]
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
