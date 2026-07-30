import asyncio
from datetime import datetime, timedelta
import logging
import os
import sys

from sqlalchemy import select
from builders import build_inline_settings_keyboard, get_main_menu, get_settings, get_timezone_keyboard
from database.session import async_session
from database.models import User, SentGame
from enums import MainMenuButtons, SettingsButtons
from services.parser import GamerPowerAPI
from aiogram import F, Bot, Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.orm.attributes import flag_modified
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


async def add_user_if_not_exists(user_id: int):
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if not user:
                session.add(User(id=user_id))
        await session.commit()


async def get_active_users():
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.is_active == True))
        return result.scalars().all()


async def get_sent_game_to_user(user_id: int, game_id: int):
    async with async_session() as session:
        result = await session.execute(select(SentGame.id).where(
            SentGame.user_id == user_id, 
            SentGame.game_id == game_id
            )
        )
        return result.scalars().first()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user_if_not_exists(message.from_user.id)
    await message.answer(text=(
        "🎮 <b>Добро пожаловать в Spiratis!</b> 🎮\n\n"
        "Я твой личный охотник за игровой халявой. Я каждый день буду присылать список <b>бесплатных</b> игр, "
        "DLC или продуктов в раннем доступе\n\n"
        "🚀 Нажми кнопку <b>🔍 Проверить</b>, чтобы увидеть текущие раздачи.\n\n"
        "В ⚙️ Настройках можно выбрать тип продуктов, платформы и устройства, указать часовой пояс, отключить ежедневные уведомления бота"
    )
        , reply_markup=get_main_menu(),
        parse_mode="HTML")


@dp.message(F.text == MainMenuButtons.SETTINGS.value)
async def settings_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return
        
    await message.answer(text=(
        "🛠 Настрой фильтры, чтобы получать только подходящие игры:\n\n"
        "📱 <b>Устройство:</b> ПК, консоли или мобильные\n\n"
        "🔌 <b>Платформа:</b> Steam, Epic Games, GOG и др.\n\n"
        "📦 <b>Тип:</b> Полные игры, DLC или раний доступ"
    ), 
    reply_markup=get_settings(user.is_active),
    parse_mode="HTML")


@dp.message(F.text == MainMenuButtons.CHECK.value)
async def check_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user_settings = user.settings
            else:
                user_settings = {}

    games = await GamerPowerAPI.get_giveaways()
    if not games:
        return await message.answer("На данный момент новых раздач нет. Попробуйте позже.", reply_markup=get_main_menu())

    games_list = await get_giveaways_list(games=games, user_settings=user_settings, uid=user_id)
    message_text, photos = get_games_msg(games_dict=games_list, user=user)
    if message_text is None:
        return await message.answer("На данный момент новых раздач нет. Попробуйте позже.", reply_markup=get_main_menu())

    try:
        await bot.send_media_group(
                chat_id=user_id,
                media=[types.InputMediaPhoto(media=photo, 
                    caption=message_text if i == 0 else "",
                    parse_mode="HTML") for i, photo in enumerate(photos)],
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке медиа-группы: {e}")
        await message.answer("Произошла ошибка при отправке уведомлений. Попробуйте позже.", reply_markup=get_main_menu())


@dp.message(F.text == SettingsButtons.DEACTIVATE.value)
async def deactivate_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user.is_active = False
                session.add(user)
        await session.commit()

    return await message.answer("🔕 <b>Уведомления отключены</b>\n\n"
        "Вы больше не будете получать оповещения. Возвращайтесь скорее, чтобы не пропустить крутые раздачи!",
        reply_markup=get_settings(user.is_active),
        parse_mode="HTML")


@dp.message(F.text == SettingsButtons.ACTIVATE.value)
async def activate_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user.is_active = True
                session.add(user)
        await session.commit()

    return await message.answer(text="🔔 <b>Уведомления включены!</b>\n\n"
        "Я снова в деле. Ожидайте уведомлений о новых играх!",
        reply_markup=get_settings(user.is_active),
        parse_mode="HTML")


@dp.message(F.text == SettingsButtons.BACK.value)
async def back_cmd(message: types.Message):
    await message.answer("Возвращаюсь в главное меню", reply_markup=get_main_menu())


# ------------------- Settings/Device -------------------

@dp.message(F.text == SettingsButtons.DEVICE.value)
async def device_settings_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user_settings = user.settings
            else:
                user_settings = {}
    
    return await message.answer("Выберите устройство", reply_markup=build_inline_settings_keyboard(
        user_settings=user_settings, 
        category="device", 
        adjust=[2, 2, 2, 2]
    ))

# ------------------- Settings/Platform -------------------

@dp.message(F.text == SettingsButtons.PLATFORM.value)
async def platform_settings_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user_settings = user.settings
            else:
                user_settings = {}
    
    return await message.answer("Выберите платформу", reply_markup=build_inline_settings_keyboard(
        user_settings=user_settings, 
        category="platform", 
        adjust=[2, 2]
    ))    

# ------------------- Settings/Type -------------------

@dp.message(F.text == SettingsButtons.TYPE.value)
async def type_settings_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user_settings = user.settings
            else:
                user_settings = {}
    
    return await message.answer("Выберите тип раздач", reply_markup=build_inline_settings_keyboard(
        user_settings=user_settings, 
        category="type", 
        adjust=[1, 1, 1]))

# --------------------------------------

@dp.callback_query(F.data.startswith("toggle:"))
async def handle_toggle(callback: types.CallbackQuery):
    category, value = callback.data.split(":")[1:]  # Разделяем данные колбэка на категорию и значение

    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, callback.from_user.id)
            if user:
                current_settings = user.settings.get(category, [])

                if value in current_settings:
                    current_settings.remove(value)
                else:
                    current_settings.append(value)

                flag_modified(user, "settings")

                # Обновляем настройки пользователя
                user.settings[category] = current_settings
                session.add(user)
        await session.commit()

    # Отправляем обновленную клавиатуру с учетом новых настроек
    await callback.message.edit_reply_markup(
        reply_markup=build_inline_settings_keyboard(
            user_settings=user.settings,
            category=category,
            adjust=[2, 2] if category != "type" else [1, 1, 1]
        )
    )

    return await callback.answer("Настройки обновлены")


@dp.message(F.text == SettingsButtons.TIMEZONE.value)
async def timezone_settings(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return
    
    return message.answer(text="Выберите часовой пояс", reply_markup=get_timezone_keyboard(user.timezone_offset))


@dp.callback_query(F.data.startswith("shift_tz:"))
async def shift_timezone(callback: types.CallbackQuery):
    new_start = int(callback.data.split(":")[1])
    
    # Просто обновляем клавиатуру на новую страницу
    await callback.message.edit_reply_markup(
        reply_markup=get_timezone_keyboard(new_start)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("set_tz:"))
async def set_timezone(callback: types.CallbackQuery):
    selected_tz = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        user.timezone_offset = selected_tz # Сохраняем в БД
        await session.commit()
        
    await callback.answer(f"✅ Часовой пояс установлен: UTC{'+' if selected_tz > 0 else ''}{selected_tz}")
    
    # Можно отредактировать текст сообщения, подтвердив выбор
    await callback.message.edit_text(
        f"✅ <b>Настройки сохранены!</b>\n\n"
        f"Ваш часовой пояс: <code>UTC {selected_tz:+}</code>\n"
        f"Теперь время завершения раздач будет отображаться корректно для вашего региона.",
        reply_markup=None,
        parse_mode="HTML"
    )


def format_date_for_user(api_date_str: str, user_offset: int) -> str:
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]

    try:
        # Пример GamerPower: "2024-05-31 23:59:59"
        dt = datetime.strptime(api_date_str, "%Y-%m-%d %H:%M:%S")
        
        # 2. Добавляем смещение пользователя
        user_dt = dt + timedelta(hours=user_offset)
        
        day = user_dt.day
        month = months_ru[user_dt.month - 1] # Месяцы в datetime начинаются с 1
        time = user_dt.strftime("%H:%M")
        
        return f"{day} {month}, {time}"
    except Exception:
        return api_date_str # Если что-то пошло не так, вернем оригинал


async def get_giveaways_list(games, user_settings: dict, uid: int):
    user_platforms = user_settings.get("platform", [])
    user_devices = user_settings.get("device", [])
    user_types = user_settings.get("type", [])

    games_dict = {}
    for game in games:
        if not game["end_date"] or game["end_date"] == "N/A":
            continue

        if user_platforms and not any(platform.lower() in game["platforms"].lower() for platform in user_platforms):
            continue

        if user_devices and not any(device.lower() in game["platforms"].lower() for device in user_devices):
            continue

        if user_types and game["type"].lower() not in [t.lower() for t in user_types]:
            continue

        async with async_session() as session:
            async with session.begin():
                sent_game = await get_sent_game_to_user(user_id=uid, game_id=game["id"])
                if sent_game:
                    continue  # Если игра уже была отправлена пользователю, пропускаем ее

                # Добавляем запись о том, что игра была отправлена пользователю
                new_sent_game = SentGame(user_id=uid, game_id=game["id"])
                session.add(new_sent_game)
                await session.commit()

        games_dict[game["id"]] = {
            "title" : game["title"],
            "image" : game["image"],
            "platforms" : game["platforms"],
            "end_date" : game["end_date"],
            "type" : game["type"],
            "open_giveaway_url" : game["open_giveaway_url"]
        }
    return games_dict


def get_games_msg(games_dict: dict, user: User):
    num = 0

    photos = []
    message = "🎁 <b>АКТУАЛЬНЫЕ РАЗДАЧИ ИГР</b> 🎁\n" 
    message += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
    for game in games_dict.values():
        num += 1

        title = game["title"]
        platforms = game["platforms"]
        g_type = game["type"]
        image = game["image"]
        game_link = game['open_giveaway_url']

        api_time = game['end_date']
        user_time = format_date_for_user(api_time, user.timezone_offset)

        if num <= 3:
            photos.append(image)

        message += (
            f"{num}️. <b>{title}</b>\n"
            f"Тип: <code>{g_type}</code> | {platforms}\n"
            f"⏳ До: <b>{user_time}</b>\n"
            f"🔗 <a href='{game_link}'>ЗАБРАТЬ ИГРУ</a>\n\n"
            f"───────────────────\n\n"
        )

    if num == 0:
        message = None
    return (message, photos)


async def daily_check_giveaways():
    logger.info("Starting daily message...")
    games = await GamerPowerAPI.get_giveaways()
    if not games:
        logger.info("New giveaways don't detected")
        return

    user_ids = await get_active_users()

    for uid in user_ids:
        async with async_session() as session:
            async with session.begin():
                user = await session.get(User, uid)
                if not user:
                    continue  # Если пользователь не найден, пропускаем его
                
        games_list = await get_giveaways_list(games=games, user_settings=user.settings, uid=uid)
        message, photos = get_games_msg(games_dict=games_list, user=user)
        if message is None:
            logger.info(f"No new giveaways for user {uid}")
            continue  # Если нет новых раздач для пользователя, пропускаем его

        try:
            await bot.send_media_group(
                chat_id=uid,
                media=[types.InputMediaPhoto(media=photo, 
                    caption=message if i == 0 else "",
                    parse_mode="HTML") for i, photo in enumerate(photos)],
            )
        except Exception as e:
            logger.error(f"Message has not sent: {e}")
            pass # Тут можно помечать user.is_active = False если бот заблокирован


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_check_giveaways,
        trigger=CronTrigger(hour=12, minute=0, second=0),
        name="daily_giveaways_check"
    )
    scheduler.start()

    await dp.start_polling(bot)
    logger.info("Bot has been started working...")

if __name__ == "__main__":
    asyncio.run(main())