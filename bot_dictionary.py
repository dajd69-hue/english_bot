import os
import time
import random
import requests

# ===== ПОЛУЧАЕМ ТОКЕН =====
# Сначала пробуем взять из переменных окружения (на сервере Railway)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Если не нашлось — пробуем загрузить из файла .env (для локальной работы)
if not TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    except ImportError:
        pass  # Если библиотека dotenv не установлена — просто игнорируем

if not TOKEN:
    print("❌ Токен не найден! Проверьте настройки на сервере.")
    exit()

# Отключаем прокси (на всякий случай)
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# ===== ЗАГРУЗКА СЛОВАРЯ =====
def load_dictionary():
    """Загружает слова из файла dictionary.txt"""
    words = []
    try:
        with open("dictionary.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        word = parts[0].strip()
                        translation = parts[1].strip()
                        example = parts[2].strip() if len(parts) >= 3 else ""
                        words.append({
                            "word": word,
                            "translation": translation,
                            "example": example
                        })
        print(f"✅ Загружено {len(words)} слов из словаря")
    except FileNotFoundError:
        print("❌ Файл dictionary.txt не найден! Использую базовый словарь.")
        words = [
            {"word": "apple", "translation": "яблоко", "example": "I eat an apple."},
            {"word": "book", "translation": "книга", "example": "She reads a book."},
        ]
    return words

WORDS = load_dictionary()
user_data = {}

def send_message(chat_id, text):
    """Отправляет сообщение в Telegram"""
    try:
        url = f"{BASE_URL}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, json=data, proxies={"http": None, "https": None})
        return response
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None

def get_updates(offset=None):
    """Получает новые сообщения от Telegram"""
    try:
        url = f"{BASE_URL}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        response = requests.get(url, params=params, proxies={"http": None, "https": None})
        return response.json().get("result", [])
    except Exception as e:
        print(f"Ошибка получения: {e}")
        return []

def handle_message(message):
    """Обрабатывает входящее сообщение"""
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # /start
    if text.startswith("/start"):
        send_message(chat_id, f"""
🎓 *Привет! Я словарь-репетитор!*

В моей базе *{len(WORDS)} слов*.

📝 *Просто напиши любое слово* — я переведу его
🔍 /find слово — поиск по словарю
📚 /words — все слова (по частям)
🧠 /quiz — викторина
📖 /dailyword — слово дня
📊 /stats — статистика
""")
        return

    # /stats
    if text.startswith("/stats"):
        send_message(chat_id, f"""
📊 *Статистика словаря:*
• Всего слов: *{len(WORDS)}*
• Примеров: *{sum(1 for w in WORDS if w['example'])}*
""")
        return

    # /words
    if text.startswith("/words"):
        page = 0
        if chat_id in user_data and "page" in user_data[chat_id]:
            page = user_data[chat_id]["page"]
        
        start = page * 20
        end = min(start + 20, len(WORDS))
        
        if start >= len(WORDS):
            user_data[chat_id]["page"] = 0
            start = 0
            end = min(20, len(WORDS))
        
        msg = f"📚 *Словарь (часть {page+1}):*\n\n"
        for w in WORDS[start:end]:
            msg += f"• *{w['word']}* — {w['translation']}\n"
        
        msg += f"\nПоказано {start+1}-{end} из {len(WORDS)} слов"
        msg += f"\n\n📌 Чтобы увидеть следующую часть, напишите /next"
        send_message(chat_id, msg)
        
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["page"] = page + 1
        return

    # /next
    if text.startswith("/next"):
        if chat_id not in user_data:
            user_data[chat_id] = {"page": 0}
        
        page = user_data[chat_id].get("page", 0)
        start = page * 20
        end = min(start + 20, len(WORDS))
        
        if start >= len(WORDS):
            send_message(chat_id, "📚 Это все слова! Начните сначала: /words")
            user_data[chat_id]["page"] = 0
            return
        
        msg = f"📚 *Словарь (часть {page+1}):*\n\n"
        for w in WORDS[start:end]:
            msg += f"• *{w['word']}* — {w['translation']}\n"
        
        msg += f"\nПоказано {start+1}-{end} из {len(WORDS)} слов"
        msg += f"\n\n📌 Следующая часть: /next"
        send_message(chat_id, msg)
        user_data[chat_id]["page"] = page + 1
        return

    # /find
    if text.startswith("/find"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, "Напиши: /find apple")
            return
        
        query = parts[1].strip().lower()
        found = []
        for w in WORDS:
            if query in w["word"].lower() or query in w["translation"].lower():
                found.append(w)
        
        if found:
            msg = f"🔍 *Найдено {len(found)} слов:*\n\n"
            for w in found[:10]:
                msg += f"• *{w['word']}* — {w['translation']}\n"
                if w['example']:
                    msg += f"  📝 {w['example']}\n"
            if len(found) > 10:
                msg += f"\n... и ещё {len(found)-10} слов"
            send_message(chat_id, msg)
        else:
            send_message(chat_id, f"❌ Слово '{query}' не найдено в словаре")
        return

    # /translate
    if text.startswith("/translate"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, "Напиши: /translate apple")
            return
        
        word = parts[1].strip().lower()
        found = False
        for w in WORDS:
            if w["word"].lower() == word:
                msg = f"📖 *{w['word']}*\n🇷🇺 {w['translation']}"
                if w['example']:
                    msg += f"\n📝 {w['example']}"
                send_message(chat_id, msg)
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ Слова '{word}' нет в словаре")
        return

    # /dailyword
    if text.startswith("/dailyword"):
        word = random.choice(WORDS)
        msg = f"""
📚 *Слово дня:*
🇬🇧 *{word['word']}*
🇷🇺 {word['translation']}
"""
        if word['example']:
            msg += f"📝 {word['example']}"
        send_message(chat_id, msg)
        return

    # /quiz
    if text.startswith("/quiz"):
        if len(WORDS) < 3:
            send_message(chat_id, "❌ В словаре слишком мало слов для викторины")
            return
        
        word = random.choice(WORDS)
        all_translations = list(set([w["translation"] for w in WORDS]))
        options = random.sample(all_translations, min(3, len(all_translations)))
        if word["translation"] not in options:
            options[0] = word["translation"]
        random.shuffle(options)
        
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["quiz_answer"] = word["translation"]
        
        msg = f"🧠 *Переведите слово:* {word['word']}\n\n"
        for i, opt in enumerate(options):
            msg += f"{i+1}. {opt}\n"
        msg += "\nНапишите номер ответа (1, 2 или 3)"
        send_message(chat_id, msg)
        return

    # /help
    if text.startswith("/help"):
        send_message(chat_id, """
📖 *Команды:*
/start — приветствие
/words — все слова
/next — следующая страница
/find слово — поиск
/translate слово — перевод
/dailyword — слово дня
/quiz — викторина
/stats — статистика
""")
        return

    # Ответ на викторину (1, 2, 3)
    if text in ["1", "2", "3"]:
        if chat_id in user_data and "quiz_answer" in user_data[chat_id]:
            correct = user_data[chat_id]["quiz_answer"]
            send_message(chat_id, f"✅ Правильный ответ: {correct}")
            del user_data[chat_id]["quiz_answer"]
        else:
            send_message(chat_id, "❌ Сначала начните викторину: /quiz")
        return

    # АВТОМАТИЧЕСКИЙ ПЕРЕВОД СЛОВА (если ничего не подошло)
    if not text.startswith('/'):
        word = text.strip().lower()
        print(f"🔍 Ищу слово: {word}")
        
        # Ищем точное совпадение
        found = False
        for w in WORDS:
            if w["word"].lower() == word:
                msg = f"📖 *{w['word']}*\n🇷🇺 {w['translation']}"
                if w['example']:
                    msg += f"\n📝 {w['example']}"
                send_message(chat_id, msg)
                found = True
                print(f"✅ Найдено: {w['word']}")
                break
        
        # Если точного нет — ищем частичное совпадение
        if not found:
            found_words = []
            for w in WORDS:
                if word in w["word"].lower():
                    found_words.append(w)
                elif word in w["translation"].lower():
                    found_words.append(w)
            
            if found_words:
                if len(found_words) == 1:
                    w = found_words[0]
                    msg = f"📖 *{w['word']}*\n🇷🇺 {w['translation']}"
                    if w['example']:
                        msg += f"\n📝 {w['example']}"
                    send_message(chat_id, msg)
                else:
                    msg = f"🔍 *Найдено {len(found_words)} слов для '{word}':*\n\n"
                    for w in found_words[:10]:
                        msg += f"• *{w['word']}* — {w['translation']}\n"
                    if len(found_words) > 10:
                        msg += f"\n... и ещё {len(found_words)-10} слов."
                send_message(chat_id, msg)
                print(f"✅ Найдено частичных совпадений: {len(found_words)}")
            else:
                send_message(chat_id, f"❌ Слово '{word}' не найдено в словаре.\n\n💡 Используйте /find {word} для поиска")
                print(f"❌ Слово не найдено: {word}")
        return

    # Если ничего не подошло
    send_message(chat_id, "🤔 Я не понял. Напишите слово для перевода или используйте /help")

def main():
    print(f"🤖 Словарь-репетитор запущен!")
    print(f"📚 Загружено {len(WORDS)} слов")
    print(f"📍 Бот доступен по ссылке: https://t.me/my_learn_english_easy_bot")
    print("💡 Для остановки нажмите Ctrl+C")
    
    last_id = 0
    while True:
        try:
            updates = get_updates(last_id + 1)
            for update in updates:
                last_id = update["update_id"]
                if "message" in update:
                    handle_message(update["message"])
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен.")
            break
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()