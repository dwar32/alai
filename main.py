from flask import Flask, request
import re
import pandas as pd
import gspread
import logging
import requests
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

PAGE_TOKENS = {
    "458871213976890": "EAAJmTjZBn47sBOZBeeLCc1cr1bZCncoL5Q9NgiSYSeYxJ4qmz9oM2uS2GxEWlq90x4NzfJ4eolIHB4dt7ePRjJHd5JdoMCytwtCsuZBeYWBmQnzg2cOd28bKZBV4q8nOE7A0ed3cFQkQSyOc9CCNR792zQAS8qnFctY74Wsf3BAFKZC25ZAKJ68ITeRv7CZCf5L3m3oIxUeoL4gK1cZA0RYdD7Kba",  # 🔁 вставь актуальный токен для Shoyo.ai
    "538954369310942": "EAAJmTjZBn47sBO9rNBVnXirzJI4aqO4VYvA334mXtUhfSSohWh2edyYxSYGcFZBCN2fHPLT5pM6sjRdQZCzZANQwZBHunNxKB069PKfoFq3ApfRvm0KJOpQetzxvuo7wCSa6hmeHPxrik66fzg7E0FVSoBIjauDlhL6PI08b5J1bNQML4MGWjH7eBr9N8UqX9xj1cbZCpMMrGsY4bKKeyjq1os"   # 🔁 вставь актуальный токен для Shoyo.nn
}

# ✅ Google Таблица
def get_sheet_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/gpt-key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1_jgw8skMLI1RH9NM051M0Lqp464QzjN5LWnlR5HgqbM").sheet1
    data = sheet.get_all_records(head=1)
    return pd.DataFrame(data)

# 🆔 Извлекаем артикул
def extract_article(text):
    match = re.search(r"\b[A-ZА-Я0-9\-]{4,}\b", text)
    return match.group(0) if match else None

# 📥 Получение caption по media_id
def get_caption_from_media(media_id: str, token: str) -> str | None:
    url = f"https://graph.facebook.com/v19.0/{media_id}"
    params = {"fields": "caption", "access_token": token}
    response = requests.get(url, params=params)
    if response.ok:
        return response.json().get("caption")
    return None

# 🔎 Поиск артикула в таблице
def search_article_in_sheet(article: str) -> str:
    df = get_sheet_data()
    if "Артикул" not in df.columns:
        return "Ошибка: колонка 'Артикул' не найдена в таблице."

    match = df[df["Артикул"].astype(str).str.lower() == article.lower()]
    if not match.empty:
        size_columns = [str(i) for i in range(19, 42)] + ["56"]
        size_columns = [col for col in size_columns if col in df.columns]
        sizes = match.iloc[0][size_columns]
        available = [size for size in sizes.index if sizes[size]]
        if available:
            return f"Товар {article} в наличии. Размеры: {', '.join(available)}"
        else:
            return f"Товар {article} найден, но размеры закончились."
    else:
        return "Артикул не найден в базе."

# 📤 Отправка ответа в Instagram
def send_reply_to_user(recipient_id, message_text, token):
    url = "https://graph.facebook.com/v19.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE",
        "access_token": token
    }
    response = requests.post(url, headers=headers, json=payload)
    logging.info("📤 Ответ отправлен: %s", response.text)

# 🔗 Webhook
@app.route("/ig-webhook", methods=["GET", "POST"])
def ig_webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == "shoyo_verify_token":
            return request.args.get("hub.challenge"), 200
        return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.get_json(force=True)
        logging.info("📩 IG Webhook пришёл: %s", data)

        try:
            changes = data["entry"][0]["changes"][0]
            value = changes["value"]
            sender_id = value.get("sender", {}).get("id")
            message = value.get("message", {}).get("text")
            attachments = value.get("message", {}).get("attachments", [])
            page_id = data["entry"][0]["id"]
            token = PAGE_TOKENS.get(page_id)

            if not token:
                logging.warning(f"Нет токена для page_id {page_id}")
                return "ok", 200

            for a in attachments:
                if a.get("type") == "share":
                    media_id = a["payload"]["id"]
                    caption = get_caption_from_media(media_id, token)

                    if not caption:
                        send_reply_to_user(sender_id, "Не удалось получить описание поста.", token)
                        return "ok", 200

                    article = extract_article(caption)
                    if not article:
                        send_reply_to_user(sender_id, "Не удалось распознать артикул.", token)
                        return "ok", 200

                    response = search_article_in_sheet(article)
                    send_reply_to_user(sender_id, response, token)
                    return "ok", 200

            if message:
                send_reply_to_user(sender_id, f"Вы написали: {message}", token)

        except Exception as e:
            logging.exception("Ошибка при обработке входящего IG сообщения")

        return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Бот активен"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
