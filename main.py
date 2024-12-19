import json
import random
import asyncio
from mailbox import Message
from telegram import KeyboardButton, ReplyKeyboardMarkup
from typing import TextIO, Text
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiogram.types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


# Состояния для рулетки
class RouletteState(StatesGroup):
    waiting_for_bet = State()
    waiting_for_amount = State()

# Укажите ваш токен Telegram-бота
TOKEN = "7831842273:AAFo70SfQ0_xkaFBlC4HC1IyMVlzxnH5JQI"
ADMIN_USERNAME = "noives2"  # Ваш юзернейм для админских команд
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения данных пользователей
DATA_FILE = "users.json"


# Загрузка или инициализация файла JSON
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_data(data):
    file: TextIO
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


# Глобальные данные пользователей
users = load_data()


# Обновление данных из файла
def reload_data():
    global users
    users = load_data()


# Создание уникального ID
def generate_unique_id():
    while True:
        user_id = random.randint(1000, 9999)
        if str(user_id) not in users:
            return user_id


# Форматирование чисел с разделением разрядов точкой
def format_number(number):
    return f"{number:,.2f}".replace(",", " ").replace(".",
                                                      ",").replace(" ", ".")


# Главное меню
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(
        aiogram.types.KeyboardButton(text="📋 Мой ID"),
        aiogram.types.KeyboardButton(text="💸 Пополнить баланс"),
        aiogram.types.KeyboardButton(text="📈 Проверить баланс"),
        aiogram.types.KeyboardButton(text="💳 Вывод средств")
    )
    builder.row(aiogram.types.KeyboardButton(text="🎮 Игры"))  # Добавляем кнопку "Игры"
    return builder.as_markup(resize_keyboard=True)



# Меню для раздела "Игры"
def get_games_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(
        aiogram.types.KeyboardButton(text="🎰 Рулетка"),

    )
    builder.row(aiogram.types.KeyboardButton(text="🔙 Назад в главное меню"))
    return builder.as_markup(resize_keyboard=True)


# Обработчик кнопки "🎮 Игры"
@dp.message(lambda msg: msg.text == "🎮 Игры")
async def games_menu_handler(message: types.Message, state=None):
    await message.answer("Вы вошли в раздел игр.", reply_markup=get_games_menu())


# Меню для рулетки
def get_roulette_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(
        aiogram.types.KeyboardButton(text="🔴 Красное"),
        aiogram.types.KeyboardButton(text="⚫ Черное"),
        aiogram.types.KeyboardButton(text="🟢 Зеленое")
    )
    builder.row(aiogram.types.KeyboardButton(text="🔙 Назад в раздел игр"))
    return builder.as_markup(resize_keyboard=True)

# Обработчик кнопки "Рулетка"
@dp.message(lambda msg: msg.text == "🎰 Рулетка")
async def roulette_handler(message: types.Message):
    await message.answer(
        "Добро пожаловать в рулетку! 🎡\n"
        "Выберите, на что хотите поставить:\n\n"
        "🔴 **Красное** — множитель: 2x\n"
        "⚫ **Черное** — множитель: 2x\n"
        "🟢 **Зеленое** — множитель: 14x\n",
        reply_markup=get_roulette_menu(),
        parse_mode="Markdown"  # Используем Markdown для форматирования текста
    )

@dp.message(lambda msg: msg.text == "🔙 Назад в раздел игр")
async def back_to_games_handler(message: types.Message, state: FSMContext):
    # Очищаем состояние, если пользователь был в процессе ввода
    await state.clear()
    await message.answer("Вы вернулись в раздел игр.", reply_markup=get_games_menu())


# Начало игры в рулетку
@dp.message(lambda msg: msg.text in ["🔴 Красное", "⚫ Черное", "🟢 Зеленое"])
async def choose_color_handler(message: types.Message, state: FSMContext):
    color_map = {"🔴 Красное": "red", "⚫ Черное": "black", "🟢 Зеленое": "green"}
    await state.update_data(color=color_map[message.text])  # Сохраняем выбранный цвет
    await state.set_state(RouletteState.waiting_for_amount)  # Устанавливаем следующее состояние
    await message.answer("Введите сумму ставки (в серебре):")


@dp.message(RouletteState.waiting_for_amount)
async def place_bet_handler(message: types.Message, state: FSMContext):
    reload_data()
    user_id = str(message.from_user.id)
    user_data = users.get(user_id)

    if not user_data:
        await message.answer("Ошибка: пользователь не найден. Пожалуйста, зарегистрируйтесь снова с помощью /start.")
        return

    # Проверяем ввод
    try:
        bet_amount = float(message.text.strip())
        if bet_amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное положительное число.")
        return

    # Проверяем баланс
    if user_data["balance"] < bet_amount:
        await message.answer("Недостаточно средств на балансе для ставки.")
        return

    # Сохраняем данные
    data = await state.get_data()
    color = data["color"]
    await state.update_data(bet=bet_amount)

    def format_number(number):
        """Форматирует число с разделением тысяч точками."""
        return "{:,.0f}".format(number).replace(",", ".")

    # Логика рулетки с измененными весами
    weights = {
        "red": 30 if color == "red" else 67.3,
        "black": 30 if color == "black" else 67.3,
        "green": 2.7
    }

    total_weight = weights["red"] + weights["black"] + weights["green"]
    normalized_weights = [weights["red"] / total_weight, weights["black"] / total_weight,
                          weights["green"] / total_weight]

    result = random.choices(
        ["red", "black", "green"],
        weights=normalized_weights,
        k=1
    )[0]
    payout_multiplier = {"red": 2, "black": 2, "green": 14}

    if color == result:
        winnings = bet_amount * payout_multiplier[result]
        user_data["balance"] += winnings - bet_amount
        save_data(users)
        await message.answer(
            f"Рулетка остановилась на {result}! 🎉 Вы выиграли {format_number(winnings)} серебра.\n"
            f"Ваш новый баланс: {format_number(user_data['balance'])}",
            reply_markup=get_roulette_menu()
        )
    else:
        user_data["balance"] -= bet_amount
        save_data(users)
        await message.answer(
            f"Рулетка остановилась на {result}. 😔 Вы проиграли {format_number(bet_amount)} серебра.\n"
            f"Ваш новый баланс: {format_number(user_data['balance'])}",
            reply_markup=get_roulette_menu()
        )

    await state.clear()


# Обработчик для кнопки "🔙 Назад в раздел игр"
@dp.message(lambda msg: msg.text == "🔙 Назад в раздел игр")
async def back_to_games_handler(message: types.Message):
    await message.answer("Вы вернулись в раздел игр.", reply_markup=get_games_menu())



# Меню с кнопкой "Назад"
def get_back_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(aiogram.types.KeyboardButton(text="🔙 Назад в главное меню"))
    return builder.as_markup(resize_keyboard=True)


# Меню для первого входа
def get_first_time_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(aiogram.types.KeyboardButton(text="💸 Пополнить баланс"))
    return builder.as_markup(resize_keyboard=True)


# Приветственное сообщение
WELCOME_MESSAGE = """Привет! 👋

Добро пожаловать в наш инвестиционный бот! 💰

Здесь ты можешь:
✅ Инвестировать своё серебро и получать 15% прироста в месяц.
✅ Следить за состоянием своего баланса в реальном времени (обновление каждую минуту).
✅ Всегда быть на связи с создателем бота для вопросов и предложений.

Если у тебя есть серебро, и ты не хочешь его потерять, сделай шаг навстречу стабильному приросту – инвестируй в наш банк! 🚀

Жми на кнопку ниже и начни приумножать своё серебро уже сегодня! 💎"""


# Команда /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    reload_data()  # Загружаем актуальные данные
    user_id = str(message.from_user.id)
    if user_id not in users:
        unique_id = generate_unique_id()
        users[user_id] = {
            "tg_username": message.from_user.username,
            "balance": 0,
            "unique_id": unique_id,
            "is_first_time": True  # Флаг первого входа
        }
        save_data(users)

        # Отправляем приветственное сообщение
        await message.answer(WELCOME_MESSAGE,
                             reply_markup=get_first_time_menu())
        await asyncio.sleep(1)  # Задержка перед отправкой следующего сообщения
        await message.answer(
            f"Ваш уникальный ID: {unique_id}\n"
            f"Используйте его для пополнения баланса.",
            reply_markup=get_main_menu())
    else:
        if users[user_id].get("is_first_time", False):
            users[user_id]["is_first_time"] = False
            save_data(users)

        await message.answer("Вы уже зарегистрированы!",
                             reply_markup=get_main_menu())


# Обработчики кнопок
@dp.message(lambda msg: msg.text == "📋 Мой ID")
async def my_id_handler(message: types.Message):
    reload_data()
    user_id = str(message.from_user.id)
    if user_id in users:
        unique_id = users[user_id]["unique_id"]
        await message.answer(f"Ваш уникальный ID: {unique_id}",
                             reply_markup=get_back_menu())
    else:
        await message.answer(
            "Вы не зарегистрированы. Нажмите /start для регистрации.")


@dp.message(lambda msg: msg.text == "💸 Пополнить баланс")
async def deposit_handler(message: types.Message):
    await message.answer(
        "Для пополнения баланса напишите сюда: @noives2\n"
        "Обязательно укажите ваш уникальный ID.",
        reply_markup=get_back_menu())


@dp.message(lambda msg: msg.text == "📈 Проверить баланс")
async def check_balance_handler(message: types.Message):
    reload_data()
    user_id = str(message.from_user.id)
    if user_id in users:
        balance = users[user_id]["balance"]
        formatted_balance = format_number(balance)
        await message.answer(
            f"Ваш текущий баланс: {formatted_balance} серебра.",
            reply_markup=get_back_menu())
    else:
        await message.answer(
            "Вы не зарегистрированы. Нажмите /start для регистрации.")


@dp.message(lambda msg: msg.text == "💳 Вывод средств")
async def withdraw_handler(message: types.Message):
    await message.answer(
        "Для вывода средств напишите сюда: @noives2\n"
        "Обязательно укажите ваш уникальный ID и сумму для вывода.",
        reply_markup=get_back_menu())


@dp.message(lambda msg: msg.text == "🔙 Назад в главное меню")
async def back_to_main_menu_handler(message: types.Message):
    await message.answer("Вы вернулись в главное меню.",
                         reply_markup=get_main_menu())


# Команды /invest и /remove для управления балансом
@dp.message(Command("invest"))
async def invest_handler(message: types.Message):
    reload_data()
    if message.from_user.username != ADMIN_USERNAME:
        await message.answer("Эта команда доступна только администратору.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Используйте команду в формате: /invest сумма ID")
        return

    try:
        sum_to_add = float(args[1])
        unique_id = args[2]
    except ValueError:
        await message.answer("Ошибка! Убедитесь, что сумма введена числом.")
        return

    for user_id, data in users.items():
        if str(data["unique_id"]) == unique_id:
            data["balance"] += sum_to_add
            save_data(users)
            formatted_balance = format_number(data["balance"])
            await message.answer(
                f"Баланс пользователя с ID {unique_id} пополнен. Новый баланс: {formatted_balance} серебра."
            )
            return

    await message.answer("Пользователь с таким ID не найден.")


@dp.message(Command("remove"))
async def remove_handler(message: types.Message):
    reload_data()
    if message.from_user.username != ADMIN_USERNAME:
        await message.answer("Эта команда доступна только администратору.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Используйте команду в формате: /remove сумма ID")
        return

    try:
        sum_to_remove = float(args[1])
        unique_id = args[2]
    except ValueError:
        await message.answer("Ошибка! Убедитесь, что сумма введена числом.")
        return

    for user_id, data in users.items():
        if str(data["unique_id"]) == unique_id:
            if data["balance"] < sum_to_remove:
                await message.answer(
                    f"Ошибка: недостаточно средств. Баланс: {format_number(data['balance'])}."
                )
                return

            data["balance"] -= sum_to_remove
            save_data(users)
            formatted_balance = format_number(data["balance"])
            await message.answer(
                f"С баланса пользователя с ID {unique_id} снято {format_number(sum_to_remove)} серебра. Новый баланс: {formatted_balance}."
            )
            return

    await message.answer("Пользователь с таким ID не найден.")


# Фоновая задача начисления процентов
async def update_balances():
    while True:
        reload_data()
        for user_id, data in users.items():
            if data["balance"] > 0:
                data["balance"] += data["balance"] * 0.000035
        save_data(users)
        await asyncio.sleep(60)


# Запуск бота
async def main():
    asyncio.create_task(update_balances())
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
