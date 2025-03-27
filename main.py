from flask import Flask, request, jsonify
import re
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_sheet_data():
    logger.info("Чтение данных из Google Sheets")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/gpt-key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1_jgw8skMLI1RH9NM051M0Lqp464QzjN5LWnlR5HgqbM").sheet1
    data = sheet.get_all_records(head=1)
    logger.info(f"Успешно считано {len(data)} строк из таблицы")
    return pd.DataFrame(data)

def extract_article(text):
    logger.info(f"Извлечение артикула из текста: {text}")
    match = re.search(r"\b[A-ZА-Я0-9\-]{4,}\b", text)
    return match.group(0) if match else None

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"Получены данные: {data}")
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        return jsonify({"response": "Ошибка обработки данных", "status": "error"})

    message = data.get("message", "")
    logger.info(f"Текст сообщения: {message}")
    article = extract_article(message)

    if not article:
        logger.info("Артикул не распознан")
        return jsonify({"response": "Не удалось распознать артикул.", "status": "ok"})

    df = get_sheet_data()

    if "Артикул" not in df.columns:
        logger.error("Колонка 'Артикул' не найдена")
        return jsonify({"response": "Ошибка: колонка 'Артикул' не найдена в таблице.", "status": "error"})

    match = df[df["Артикул"].astype(str).str.lower() == article.lower()]

    if not match.empty:
        size_columns = [str(i) for i in range(19, 42)] + ["56"]
        size_columns = [col for col in size_columns if col in df.columns]
        sizes = match.iloc[0][size_columns]
        available_sizes = [size for size in sizes.index if sizes[size]]
        logger.info(f"Артикул {article} найден. Доступные размеры: {available_sizes}")
        if available_sizes:
            return jsonify({
                "response": f"Товар {article} есть в наличии. Размеры: {', '.join(available_sizes)}",
                "status": "ok"
            })
        else:
            return jsonify({"response": f"Товар {article} найден, но все размеры распроданы.", "status": "ok"})

    logger.info(f"Артикул {article} не найден в базе.")
    return jsonify({"response": "Артикул не найден в базе.", "status": "ok"})

@app.route("/", methods=["GET"])
def index():
    return "Бот активен"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
