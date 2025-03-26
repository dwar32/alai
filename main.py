from flask import Flask, request, jsonify
import requests
import pandas as pd
import re

app = Flask(__name__)

# Загружаем таблицу остатков
df = pd.read_excel("Остатки_бот.xlsx")

# Настройки Instagram
INSTAGRAM_TOKEN = "ВАШ_ИНСТАГРАМ_ТОКЕН"
API_VERSION = "v19.0"

def extract_article(text):
    match = re.search(r'артикул[:\s]*([A-Za-z0-9\-\/]+)', text, re.IGNORECASE)
    return match.group(1) if match else None

def find_product_by_article(df, article):
    result = df[df['Unnamed: 4'] == article]
    if result.empty:
        return None
    row = result.iloc[0]
    return f"""📦 Найден товар:

🆔 Артикул: {row['Unnamed: 4']}
📝 Описание: {row['Unnamed: 5']}
🎨 Цвет: {row['Unnamed: 6']}
🧒 Пол: {row['Unnamed: 7']}
☀️ Сезон: {row['Unnamed: 8']}
📦 Остаток: {int(row['Unnamed: 32'])} шт
💸 Цена: {int(row['Unnamed: 33'])} тг
"""

@app.route("/check_post", methods=["GET"])
def check_post():
    post_id = request.args.get("post_id")
    if not post_id:
        return jsonify({"error": "Передайте параметр ?post_id=..."})

    url = f"https://graph.facebook.com/{API_VERSION}/{post_id}?fields=caption&access_token={INSTAGRAM_TOKEN}"
    resp = requests.get(url)
    if not resp.ok:
        return jsonify({"error": "Не удалось получить пост", "details": resp.text}), 400

    caption = resp.json().get("caption", "")
    article = extract_article(caption)

    if not article:
        return jsonify({"message": "❌ Артикул не найден в описании поста."})

    product = find_product_by_article(df, article)
    if not product:
        return jsonify({"message": f"🛑 Артикул {article} не найден в базе."})

    return jsonify({"message": product})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
