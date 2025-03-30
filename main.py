from flask import Flask, request, jsonify
import re
import pandas as pd
import gspread
import logging
import requests
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

ACCESS_TOKEN = "EAAJjA01uR54BO4yT2zWAzWA8HOqfBnHylvb4cokZAZBvA0E4W12ngKYHlwJdQFhEutqGvxiEHLTGhdm799ZAvqDAtHune9LTvLsWNd0mHdqIZB4zyjZCFZAZAoZCyZCaRZC7Mur8ZCKebI9iSZCtSEhicROOxP3yiexnJhUEOUDpDcPTaqakU6G0JkK2osqLhZAz0M9QdH28yU6vmLmR3NP6MuAZDZD"  # вставь сюда рабочий токен

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

def get_caption_from_media(media_id: str) -> str | None:
    url = f"https://graph.facebook.com/v19.0/{media_id}"
    params = {
        "fields": "caption",
        "access_token": ACCESS_TOKEN
    }
    response = requests.get(url, params=params)
    if response.ok:
        return response.json().get("caption")
    return None

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logging.info("Получены данные: %s", data)

        if not isinstance(data, dict):
            return jsonify({"response": "Неверный формат входных данных", "status": "error"})

        # Получаем media_id из Make
        media_id = data.get("media_id")
        if not media_id:
            return jsonify({"response": "media_id не передан", "status": "error"})

        caption = get_caption_from_media(media_id)
        if not caption:
            return jsonify({"response": "Не удалось получить caption по media_id", "status": "error"})

        article = extract_article(caption)
        if not article:
            return jsonify({"response": "Артикул не найден в тексте поста", "status": "ok"})

        df = get_sheet_data()
        if "Артикул" not in df.columns:
            return jsonify({"response": "Колонка 'Артикул' не найдена в таблице", "status": "error"})

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
        else:
            return jsonify({"response": "Артикул не найден в базе.", "status": "ok"})

    except Exception as e:
        logging.exception("Ошибка при обработке запроса")
        return jsonify({"response": "Ошибка обработки данных", "status": "error"})

@app.route("/", methods=["GET"])
def index():
    return "Бот активен"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
