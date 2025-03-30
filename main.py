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

@app.route("/ig-webhook", methods=["GET", "POST"])
def ig_webhook():
    if request.method == "GET":
        verify_token = "shoyo_verify_token"  # токен для Meta верификации
        if request.args.get("hub.verify_token") == verify_token:
            return request.args.get("hub.challenge"), 200
        return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.get_json(force=True)
        logging.info("📩 IG Webhook пришёл: %s", data)

        try:
            messaging = data["entry"][0]["messaging"][0]
            sender_id = messaging["sender"]["id"]
            attachments = messaging.get("message", {}).get("attachments", [])

            for a in attachments:
                if a.get("type") == "share":
                    media_id = a["payload"]["id"]

                    # Вызываем основной /webhook
                    r = requests.post("https://alai-2.onrender.com/webhook", json={"media_id": media_id})
                    result = r.json()
                    message_text = result.get("response", "Извините, произошла ошибка.")

                    # Отправляем ответ в директ
                    send_reply_to_user(sender_id, message_text)

        except Exception as e:
            logging.exception("Ошибка обработки входящего сообщения")

        return "ok", 200

def send_reply_to_user(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE",
        "access_token": ACCESS_TOKEN
    }
    response = requests.post(url, headers=headers, json=payload)
    logging.info("Ответ отправлен: %s", response.text)

@app.route("/", methods=["GET"])
def index():
    return "Бот активен"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
