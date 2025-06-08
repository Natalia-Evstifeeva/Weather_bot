#Все нужные библиотеки
import telebot
import requests
import json
import os
import datetime
import time

from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from telebot import custom_filters


#Мои тайные данные
class Config:
    bot_token = '7990356597:AAGTX7a0tbvC4SsIQ3q3F5nqhS7HoFVG2A0'
    weather_api = 'a7362a9aee7f1dcc756ca733be85b29d'


#Инициализация
config = Config() #создаю экземпляр конфигурации
storage = StateMemoryStorage() #для того, чтобы хранить состояния
bot = telebot.TeleBot(config.bot_token, state_storage=storage)#создаю экземпляр бота

#Создаю константы файлов
file_with_fav = 'user_favorites.json' #названия говорящие (создаю файлы)
file_for_logging = 'bot_activity.log'
file_for_cache = 'weather_cache.json'
bot_stats_file = 'bot_stats.json'


#Загружаю данные из джейсон файла
def load_data(filename, default=None):
    if default is None:
        default = {}
    if os.path.exists(filename): #проверка на то, что файл вообще существует
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default


#Сохраняю данные в джейсон файл
def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


#Загружаю избранные города, кэш
user_favorites = load_data(file_with_fav)
weather_cache = load_data(file_for_cache)
bot_stats = load_data(bot_stats_file, {
    "users": {}, #здесь тоже все названия словарей говорящие
    "weather_requests": 0,
    "fav_added": 0,
    "fav_removed": 0,
    "commands": {}
})


#Логирование
def log_action(user_id, username, action):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") #записываю текущее время
    log_entry = f"{timestamp} | UserID: {user_id} | Username: @{username} | Action: {action}\n"

    #Здесь обновляется статистика
    if user_id not in bot_stats["users"]:
        bot_stats["users"][user_id] = {
            "first_seen": timestamp,
            "last_seen": timestamp,
            "username": username
        }
    else:
        bot_stats["users"][user_id]["last_seen"] = timestamp

    action_type = action.split(":")[0]
    bot_stats["commands"][action_type] = bot_stats["commands"].get(action_type, 0) + 1
#Записываю в лог файл
    with open(file_for_logging, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    save_data(bot_stats, bot_stats_file)#сохраняю новую статистику


#Middleware для логирования входящих (как я поняла)
class LoggingMiddleware:
    def __init__(self, bot):
        self.bot = bot

    def pre_process_message(self, message): #предобработка
        user = message.from_user
        log_action(user.id, user.username, f"Received: {message.text}")

    def post_process_message(self, message, result): #постобработка
        user = message.from_user
        log_action(user.id, user.username, f"Processed: {message.text}")


bot.setup_middleware(LoggingMiddleware(bot))

#Фильтры под кастом (я не очень поняла, как это работает, но вроде нейронка написала вариант, который ничего не поломал)
class IsCommand(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_command'
    @staticmethod
    def check(message: telebot.types.Message):
        return message.text and message.text.startswith('/')

#Регистрация фильтров
bot.add_custom_filter(IsCommand())

#Клавиатура, которая видна постоянно (кроме момента набора текста)
def create_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)#поганяю размер
    #Эстетик кнопочки
    buttons = [
        'Показать погоду 🌤️',
        'Перейти на сайт 🔗',
        'Добавить в избранное ⭐',
        'Удалить из избранного ❌',
        'Избранное 📋'
    ]
    markup.add(*buttons)
    return markup

global_keyboard = create_keyboard()


#Обрабатываю команды начала работы и приветствия
@bot.message_handler(commands=['start', 'hello'])
def start(message):
    log_action(message.from_user.id, message.from_user.username, f"Command: {message.text}")#не забываем про логирование
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!', reply_markup=global_keyboard)
    help_command(message)#сразу вызываю /help, чтобы пользователь увидел, что к чему


@bot.message_handler(commands=['help'])
def help_command(message):
    log_action(message.from_user.id, message.from_user.username, "Command: /help")
    help_text = (
        "🚀 Доступные команды:\n"
        "/start - приветствие\n"
        "/help - список команд\n"
        "/show_weather - показать погоду\n"
        "/website - открыть сайт\n"
        "/add_to_fav - добавить в избранное\n"
        "/delete_from_fav - удалить из избранного\n"
        "/show_fav - показать избранное"
    )
    bot.send_message(message.chat.id, help_text, reply_markup=global_keyboard)


#Обрабатываю вызов сайта
@bot.message_handler(commands=['website'])
def website(message):
    log_action(message.from_user.id, message.from_user.username, "Command: /website")
    #Делаю inline кнопку
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Открыть сайт", url="https://openweathermap.org/city/2643743"))
    bot.send_message(message.chat.id, "Нажмите кнопку, чтобы перейти на сайт:", reply_markup=markup)
    # Добавляем основную клавиатуру в следующем сообщении
    bot.send_message(message.chat.id, "Чем еще могу помочь?", reply_markup=global_keyboard)

#Обрабатываю добавление в избранное
@bot.message_handler(commands=['add_to_fav'])
def add_fav(message):
    log_action(message.from_user.id, message.from_user.username, "Command: /add_to_fav")
    msg = bot.send_message(message.chat.id, "Введите город для добавления в избранное:", reply_markup=global_keyboard)
    bot.register_next_step_handler(msg, process_add_fav)

#Обрабатываю ввод города для добавления в избранное
def process_add_fav(message):
    city = message.text.strip().lower()
    log_action(message.from_user.id, message.from_user.username, f"Add to fav: {city}")
    chat_id = str(message.chat.id)
    if chat_id not in user_favorites:
        user_favorites[chat_id] = []

    if city not in user_favorites[chat_id]: #проверка на то, чтобы не повторялся город (уже не был в избранном)
        user_favorites[chat_id].append(city)
        save_data(user_favorites, file_with_fav)
        #опять обновляю статистику
        bot_stats['fav_added'] += 1
        save_data(bot_stats, bot_stats_file)
        #вывожу подтверждение, что город был добавлен в избр, чтобы пользователь точно понял, что произошло
        bot.send_message(message.chat.id, f"✅ Город {city.capitalize()} добавлен в избранное!", reply_markup=global_keyboard)#чтобы пользователю красиво отображалось с большой буквы
    else: #если уже в избранном
        bot.send_message(message.chat.id, f"⚠️ Город {city.capitalize()} уже в избранном!\n \nЕсли хотите добавить другой город в избранное:\nвызовите команду /add_to_fav \nили нажмите на соответствующую кнопку", reply_markup=global_keyboard)

#Обрабатываю удаление из избранного (механика аналогичная добавлению, только с удалением)
@bot.message_handler(commands=['delete_from_fav'])
def del_fav(message):
    log_action(message.from_user.id, message.from_user.username, "Command: /delete_from_fav")
    chat_id = str(message.chat.id)
    if chat_id in user_favorites and user_favorites[chat_id]:
        cities = "\n".join([city.capitalize() for city in user_favorites[chat_id]])
        msg = bot.send_message(message.chat.id, f"Ваши избранные города:\n{cities}\nВведите город для удаления:", reply_markup=global_keyboard)
        bot.register_next_step_handler(msg, process_del_fav)
    else:
        bot.send_message(message.chat.id, "ℹ️ У вас нет городов в избранном", reply_markup=global_keyboard)

#Обрабатываю ввод города для удаления из избранного
def process_del_fav(message):
    city = message.text.strip().lower()
    log_action(message.from_user.id, message.from_user.username, f"Delete from fav: {city}")
    chat_id = str(message.chat.id)

    if chat_id in user_favorites and city in user_favorites[chat_id]:
        user_favorites[chat_id].remove(city)
        save_data(user_favorites, file_with_fav)
        bot_stats['fav_removed'] += 1
        save_data(bot_stats, bot_stats_file)
        bot.send_message(message.chat.id, f"✅ Город {city.capitalize()} удален из избранного!", reply_markup=global_keyboard)
    else:
        bot.send_message(message.chat.id, f"❌ Город {city.capitalize()} не найден в избранном", reply_markup=global_keyboard)

#Обрабатываю отображение избранного (чтоб все было красиво, с заглавной буквы)
@bot.message_handler(commands=['show_fav'])
def show_fav(message):
    log_action(message.from_user.id, message.from_user.username, "Command: /show_fav")
    chat_id = str(message.chat.id)
    if chat_id in user_favorites and user_favorites[chat_id]:
        cities = "\n".join([city.capitalize() for city in user_favorites[chat_id]])
        bot.send_message(message.chat.id, f"⭐ Ваше избранное:\n{cities}", reply_markup=global_keyboard)
    else:
        bot.send_message(message.chat.id, "ℹ️ У вас пока нет избранных городов", reply_markup=global_keyboard)


#Обрабатываю погоду с кэшированием
@bot.message_handler(commands=['show_weather'])
def get_weather_command(message):
    log_action(message.from_user.id, message.from_user.username, "Command: /show_weather")
    msg = bot.send_message(message.chat.id, "Введите название города (на русском):", reply_markup=global_keyboard)
    bot.register_next_step_handler(msg, process_weather_request)

#Обрабатываю вывод города для запроса погоды
def process_weather_request(message):
    city = message.text.strip()
    log_action(message.from_user.id, message.from_user.username, f"Weather request: {city}")
    get_weather(message, city)

#Получаю погодные данные по указанному городу
def get_weather(message, city):
    # Проверка кэша
    city_key = city.lower()
    current_time = time.time()

    if city_key in weather_cache:
        cached = weather_cache[city_key]
        if current_time - cached['timestamp'] < 300:# 5 минут актуальность кэша
            send_weather_info(message, city, cached['data'])
            return

    # Запрос к API с обработкой ошибок
    try:
        res = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={config.weather_api}&units=metric',
            timeout=10 #даю таймаут 10 секунд
        )
        res.raise_for_status()

        data = res.json()
        weather_cache[city_key] = {
            'data': data,
            'timestamp': current_time
        }
        save_data(weather_cache, file_for_cache)

        bot_stats['weather_requests'] += 1 #опять обновляю статистику
        save_data(bot_stats, bot_stats_file)

        send_weather_info(message, city, data)
#Здесь обрабатываются исключения, со ссылкой на то, что сделать, чтобы программа дальше исполнила команду
    except requests.exceptions.Timeout:
        bot.reply_to(message, 'Превышено время ожидания ответа от сервера погоды\nВероятно город введен не верно', reply_markup=global_keyboard)
        bot.send_message(message.chat.id, 'Для получения информации о другом городе, вызовете команду /show_weather или нажмите на кнопку Показать погоду 🌤️')
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f'Ошибка при получении данных: {str(e)}\nВероятно город введен не верно', reply_markup=global_keyboard)
        bot.send_message(message.chat.id,'Для получения информации о другом городе, вызовете команду /show_weather или нажмите на кнопку Показать погоду 🌤️')
    except Exception as e:
        bot.reply_to(message, f'Неизвестная ошибка: {str(e)}', reply_markup=global_keyboard)

#Форматирую и отправляю всю инфу по погоде
def send_weather_info(message, city, data):
    temp = data["main"]["temp"]
    temp_feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    weather_info = (
        f"🌤️ Погода в городе {city.capitalize()}:\n"
        f"Температура: {round(temp)}°C\n"
        f"Ощущается как: {round(temp_feels_like)}°C\n"
        f"Влажность: {humidity}%\n"
        f"Скорость ветра: {wind_speed} м/c"
    )

    bot.reply_to(message, weather_info, reply_markup=global_keyboard)

    bot.send_message(message.chat.id, "Выберите следующее действие:", reply_markup=global_keyboard)


#Обрабатываю callback запросы
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_fav_'))
def callback_add_fav(call):
    city = call.data.split('_')[2]
    chat_id = str(call.message.chat.id)

    if chat_id not in user_favorites:
        user_favorites[chat_id] = []

    if city not in user_favorites[chat_id]:
        user_favorites[chat_id].append(city)
        save_data(user_favorites, file_with_fav)
        bot_stats['fav_added'] += 1
        save_data(bot_stats, bot_stats_file)
        #опять показываю пользователю, что было сделано, для понятности
        bot.answer_callback_query(call.id, f"✅ Город {city.capitalize()} добавлен в избранное!")
    else:
        bot.answer_callback_query(call.id, f"⚠️ Город {city.capitalize()} уже в избранном!\n \nЕсли хотите добавить другой город в избранное:\nвызовите команду /add_to_fav \nили нажмите на кнопку Добавить в избранное ⭐")

    # Обновляем клавиатуру
    bot.send_message(call.message.chat.id, "Чем еще могу помочь?", reply_markup=global_keyboard)


#Обрабатываю кнопки
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    log_action(message.from_user.id, message.from_user.username, f"Button: {message.text}")
    #текст преобразую в команду для выполнения
    if message.text == 'Показать погоду 🌤️':
        msg = bot.send_message(message.chat.id, "Введите название города (на русском):", reply_markup=global_keyboard)
        bot.register_next_step_handler(msg, process_weather_request)

    elif message.text == 'Перейти на сайт 🔗':
        website(message)

    elif message.text == 'Добавить в избранное ⭐':
        add_fav(message)

    elif message.text == 'Удалить из избранного ❌':
        del_fav(message)

    elif message.text == 'Избранное 📋':
        show_fav(message)

    else:#на всякий случай
        bot.send_message(message.chat.id, "❌ Неизвестная команда, используйте кнопки или /help", reply_markup=global_keyboard)


if __name__ == '__main__':
    bot.add_custom_filter(telebot.custom_filters.StateFilter(bot)) #рега фильтра состояний
    bot.infinity_polling()#чтобы бот всегда был активен