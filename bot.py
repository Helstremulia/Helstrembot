import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
import openai
from geopy.geocoders import Nominatim

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

user_data = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Введи свою дату рождения в формате ГГГГ-ММ-ДД:")
    user_data[message.chat.id] = {}

@dp.message_handler(lambda message: message.chat.id in user_data and 'date' not in user_data[message.chat.id])
async def get_date(message: types.Message):
    user_data[message.chat.id]['date'] = message.text
    await message.answer("Теперь введи время рождения (например, 14:30):")

@dp.message_handler(lambda message: message.chat.id in user_data and 'time' not in user_data[message.chat.id])
async def get_time(message: types.Message):
    user_data[message.chat.id]['time'] = message.text
    await message.answer("И наконец, город рождения:")

@dp.message_handler(lambda message: message.chat.id in user_data and 'place' not in user_data[message.chat.id])
async def get_place(message: types.Message):
    chat_id = message.chat.id
    user_data[chat_id]['place'] = message.text

    date = user_data[chat_id]['date']
    time = user_data[chat_id]['time']
    place = user_data[chat_id]['place']

    # Получаем координаты по городу
    geolocator = Nominatim(user_agent="celestia_bot")
    location = geolocator.geocode(place)
    if not location:
        await message.answer("Не удалось найти город. Попробуй снова.")
        return

    pos = GeoPos(location.latitude, location.longitude)
    dt = Datetime(f"{date} {time}", 'UTC')
    chart = Chart(dt, pos)

    summary = ""
    for obj in ['SUN', 'MOON', 'ASC']:
        summary += f"{obj}: {chart.get(obj)}\n"

    # Отправляем в OpenAI для анализа
    ai_prompt = f"""
Вот базовые данные натальной карты:
{summary}

Проанализируй основные черты личности по этим данным.
"""

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": ai_prompt}]
        )
        response = completion.choices[0].message.content.strip()
        await message.answer(f"Вот твой астрологический анализ от ИИ:\n\n{response}")
    except Exception as e:
        await message.answer(f"Ошибка при обращении к OpenAI: {e}")

    user_data.pop(chat_id)
