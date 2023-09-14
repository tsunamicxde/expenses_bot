import logging
from aiogram import Bot, Dispatcher, types, executor
import psycopg2

from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import host, port, db_name, user, password, TOKEN

from datetime import datetime
import os

import matplotlib.pyplot as plt


bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())

conn = psycopg2.connect(
    host=host,
    port=port,
    dbname=db_name,
    user=user,
    password=password
)
cursor = conn.cursor()

with open('create_users_table.sql', 'r') as sql_config:
    create_table_query = sql_config.read()

cursor.execute(create_table_query)

conn.commit()

all_categories = ['Продукты', 'Ресторан', 'Фастфуд', 'Доставка', 'Кофе',
                  'Одежда', 'Здоровье', 'Образование', 'Подписки', 'Другое']

time_list = ['DAY', 'WEEK', 'MONTH', 'YEAR']


@dp.message_handler(commands=['start', 'help'])
async def cmd_start(message: types.Message):
    menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    menu_keyboard.row("/expenses_list", "/statistics")
    menu_keyboard.row("/help")

    await message.reply("Привет! Я бот, который сохраняет ваши расходы\n\n"
                        "Отправьте расход в виде: сумма, описание\n"
                        "Например: 250, кофе\n\n"
                        "Команды:\n"
                        "/expenses_list - посмотреть список расходов за период\n"
                        "/statistics - посмотреть расходы по категориям\n"
                        "/help - помощь", reply_markup=menu_keyboard)


@dp.message_handler(commands=['statistics'])
async def get_statistics(message: types.Message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    day = types.InlineKeyboardButton("День", callback_data="DAY_")
    week = types.InlineKeyboardButton("Неделя", callback_data="WEEK_")
    month = types.InlineKeyboardButton("Месяц", callback_data="MONTH_")
    year = types.InlineKeyboardButton("Год", callback_data="YEAR_")
    markup.add(day, week, month, year)

    await message.reply(f"Выберите период статистики:\n", reply_markup=markup)


@dp.message_handler(commands=['expenses_list'])
async def expenses_list(message: types.Message):

    markup = types.InlineKeyboardMarkup(row_width=1)
    day = types.InlineKeyboardButton("День", callback_data="DAY")
    week = types.InlineKeyboardButton("Неделя", callback_data="WEEK")
    month = types.InlineKeyboardButton("Месяц", callback_data="MONTH")
    year = types.InlineKeyboardButton("Год", callback_data="YEAR")
    markup.add(day, week, month, year)

    await message.reply(f"Выберите период статистики:\n", reply_markup=markup)


@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: types.Message, state: FSMContext):

    try:
        expense_list = message.text.split(", ")
        async with state.proxy() as data:
            data['user_id'] = message.chat.id
            data['expense'] = float(expense_list[0].replace(" ", ""))
            data['description'] = expense_list[1].strip()

        markup = types.InlineKeyboardMarkup(row_width=1)
        products = types.InlineKeyboardButton("Продукты 🛒", callback_data="Продукты")
        rest = types.InlineKeyboardButton("Ресторан 🍴", callback_data="Ресторан")
        food = types.InlineKeyboardButton("Фастфуд 🍔", callback_data="Фастфуд")
        delivery = types.InlineKeyboardButton("Доставка 🚴🏻‍♂️", callback_data="Доставка")
        coffee = types.InlineKeyboardButton("Кофе 🧋‍", callback_data="Кофе")
        clothes = types.InlineKeyboardButton("Одежда 👕‍", callback_data="Одежда")
        health = types.InlineKeyboardButton("Здоровье 💊‍", callback_data="Здоровье")
        education = types.InlineKeyboardButton("Образование 🎓‍", callback_data="Образование")
        subscribe = types.InlineKeyboardButton("Подписки 🎟", callback_data="Подписки")
        other = types.InlineKeyboardButton("Другое 0️⃣", callback_data="Другое")
        cancel = types.InlineKeyboardButton("Отмена ❌", callback_data="cancel")
        markup.add(products, rest, food, delivery, coffee, clothes, health, education, subscribe, other, cancel)

        await message.reply(f"Выберите категорию траты:\n", reply_markup=markup)
    except ValueError as ex:
        await message.reply("Введите расход в виде: сумма, описание\n"
                            "Например: 250, кофе")
        print(ex)


@dp.callback_query_handler(lambda callback_query: True)
async def callback(call, state: FSMContext):
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if call.data == "accept":
        try:
            async with state.proxy() as data:
                user_id = data.get('user_id')
                expense = data.get('expense')
                description = data.get('description')
                category = data.get('category')
            await bot.send_message(call.message.chat.id, f"Вы добавили расход:\n"
                                                         f"Сумма: {expense}\n"
                                                         f"Описание: {description}\n"
                                                         f"Категория: {category}")

            insert_query = '''
                                INSERT INTO users (user_id, expense, description, category, datetime)
                                VALUES (%s, %s, %s, %s, NOW());
                           '''
            cursor.execute(insert_query, (user_id, expense, description, data['category']))
            conn.commit()

        except Exception as ex:
            print(ex)
    elif call.data in all_categories:
        try:
            async with state.proxy() as data:
                expense = data.get('expense')
                description = data.get('description')
                data['category'] = call.data

            markup = types.InlineKeyboardMarkup(row_width=1)
            item = types.InlineKeyboardButton("Принять ✅", callback_data="accept")
            item2 = types.InlineKeyboardButton("Отмена ❌", callback_data="cancel")
            markup.add(item, item2)

            await bot.send_message(call.message.chat.id, f"Вы собираетесь добавить запись:\n"
                                                         f"Сумма: {expense}\n"
                                                         f"Описание: {description}\n"
                                                         f"Категория: {data['category']}", reply_markup=markup)
        except Exception as ex:
            print(ex)
    elif str(call.data).replace("_", "") in time_list:

        user_id = call.message.chat.id

        period = str(call.data).replace("_", "")
        current_date = datetime.now()

        date_name = ""

        if period == "DAY":
            current_date = datetime.now().date()
            date_name = f"Сегодня" \
                        f"({datetime.now().strftime('%d.%m.%y')})"
        elif period == "WEEK":
            current_date = datetime.now().isocalendar()[1]
            date_name = "Неделя"
        elif period == "MONTH":
            current_date = datetime.now().month
            date_name = f"Месяц" \
                        f"({datetime.now().month}.{datetime.now().year})"
        elif period == "YEAR":
            current_date = datetime.now().year
            date_name = f"Год" \
                        f"({datetime.now().year})"
        else:
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")

        expenses_query = f"""
                                SELECT expense, description, category, datetime
                                FROM users
                                WHERE user_id = %s
                                AND EXTRACT({period} FROM datetime)::integer = %s
                                ORDER BY datetime
                          """

        if period == "DAY":
            cursor.execute(expenses_query, (user_id, current_date.day))
        else:
            cursor.execute(expenses_query, (user_id, current_date))

        if cursor.rowcount > 0:
            rows = cursor.fetchall()

            total_expense_query = f"""
                SELECT SUM(expense)
                FROM users
                WHERE user_id = %s
                AND EXTRACT({period} FROM datetime)::integer = %s
            """

            if period == "DAY":
                cursor.execute(total_expense_query, (user_id, current_date.day))
            else:
                cursor.execute(total_expense_query, (user_id, current_date))

            total_expense = cursor.fetchone()[0]

            statistics_by_categories = []
            data_by_date = {}

            if "_" in str(call.data):
                for row in rows:
                    amount, description, category, date = row
                    statistics_by_categories.append({
                        'category': category, 'amount': amount,
                    })

                category_totals = {}

                for entry in statistics_by_categories:
                    category = entry['category']
                    amount = entry['amount']

                    if category in category_totals:
                        category_totals[category] += amount
                    else:
                        category_totals[category] = amount

                categories = list(category_totals.keys())
                amounts = list(category_totals.values())

                plt.figure(figsize=(8, 8))
                plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=140)

                title_message = f"Распределение расходов по категориям\n" \
                                f"Период: {date_name}"
                plt.title(title_message)
                plt.savefig(f'{user_id}_statistics.png')
                photo = open(f'{user_id}_statistics.png', 'rb')
                await bot.send_photo(call.message.chat.id, photo)
                os.remove(f'{user_id}_statistics.png')

                string = ""
                for i in range(len(categories)):
                    string += f"{categories[i]}: {amounts[i]}\n\n"
                await bot.send_message(call.message.chat.id, f"Общие расходы по категориям:\n\n"
                                                             f"{string}"
                                                             f"Всего потрачено за период: {total_expense}")
            else:
                for row in rows:
                    amount, description, category, date = row
                    date_key = date.replace(hour=0, minute=0, second=0, microsecond=0)

                    if date_key not in data_by_date:
                        data_by_date[date_key] = []

                    data_by_date[date_key].append(
                        f"\nСумма: {amount}\nОписание: {description}\nКатегория: {category}\n"
                        f"Время: {date.strftime('%H:%M')}")

                string = ""
                for date, data_list in data_by_date.items():
                    string += f"Дата: {date.strftime('%d.%m.%y')}\n"
                    string += "\n".join(data_list) + "\n\n"

                await bot.send_message(call.message.chat.id, f"Статистика расходов:\n"
                                                             f"Период: {date_name}\n\n"
                                                             f"{string}"
                                                             f"Всего потрачено за период: {total_expense}")
        else:
            await bot.send_message(call.message.chat.id, f"За указанный период нет записей")

    elif call.data == "cancel":
        await bot.send_message(call.message.chat.id, f"Вы удалили запись")
    else:
        await bot.send_message(call.message.chat.id, "Что-то пошло не так")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
