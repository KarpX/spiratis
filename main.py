import asyncio
from datetime import datetime
import logging
import os
import sys

from sqlalchemy import select
from builders import build_inline_keyboard, build_inline_settings_keyboard, get_activate_btn, get_main_menu, get_settings
from database.session import async_session
from database.models import User, SentGame
from enums import DeviceSettingsButtons, MainMenuButtons, PlatformSettingsButtons, SettingsButtons, TypeSettingsButtons
from services.parser import GamerPowerAPI
from aiogram import F, Bot, Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.orm.attributes import flag_modified

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Явно указываем поток вывода
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
    await message.answer("Привет! Я Spiratis. Я буду присылать тебе уведомления о бесплатных играх в Steam и других магазинах!"
        , reply_markup=get_main_menu())


@dp.message(F.text == MainMenuButtons.SETTINGS.value)
async def settings_cmd(message: types.Message):
    await message.answer("Что Вы хотите настроить?\n1. Устройство (ПК, PS, Xbox и т.д.)\n2. Платформа (Steam, EpicGames и т.д.)\n3. Тип (Игра, DLC, Beta)", 
    reply_markup=get_settings())


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
        return await message.answer("На данный момент раздач нет. Попробуйте позже.", reply_markup=get_main_menu())

    games_list = await get_giveaways_list(games=games, user_settings=user_settings, uid=user_id)
    message_text, photos = get_games_msg(games_dict=games_list)
    if message_text is None:
        return await message.answer("На данный момент раздач нет. Попробуйте позже.", reply_markup=get_main_menu())

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

    return await message.answer("Уведомления отключены. Вы больше не будете получать уведомления о раздачах.", reply_markup=get_activate_btn())


@dp.message(F.text == "✅ Включить уведомления")
async def activate_cmd(message: types.Message):
    user_id = message.from_user.id
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user.is_active = True
                session.add(user)
        await session.commit()

    return await message.answer("Уведомления включены. Вы снова будете получать уведомления о раздачах.", reply_markup=get_main_menu())


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


def get_games_msg(games_dict: dict):
    num = 0

    photos = []
    message = "Текущие раздачи: \n\n"
    for game in games_dict.values():
        num += 1

        title = game["title"]
        platforms = game["platforms"]
        g_type = game["type"]
        image = game["image"]

        if num <= 3:
            photos.append(image)

        message += (
            f"{num}️. <b>{title}</b>\n"
            f"Тип: <code>{g_type}</code> | {platforms}\n"
            f"⏳ До: <b>{game['end_date']}</b>\n"
            f"🔗 <a href='{game['open_giveaway_url']}'>ЗАБРАТЬ ИГРУ</a>\n\n"
            f"───────────────────\n\n"
        )

    if num == 0:
        message = None
    return (message, photos)


async def check_giveaways():
    while True:
        games = await GamerPowerAPI.get_giveaways()
        if not games:
            logger.info("New giveaways don't detected")
            await asyncio.sleep(40)  # Ждем 30 минут перед следующей проверкой 1800 sec
            continue

        user_ids = await get_active_users()

        for uid in user_ids:
            async with async_session() as session:
                async with session.begin():
                    user = await session.get(User, uid)
                    if not user:
                        continue  # Если пользователь не найден, пропускаем его
                    
            games_list = await get_giveaways_list(games=games, user_settings=user.settings, uid=uid)
            message, photos = get_games_msg(games_dict=games_list)
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

        await asyncio.sleep(40)

async def main():
    asyncio.create_task(check_giveaways())
    await dp.start_polling(bot)
    logger.info("Bot has been started working...")

if __name__ == "__main__":
    asyncio.run(main())