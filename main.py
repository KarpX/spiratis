import asyncio
import logging
import os
import sys

from sqlalchemy import select
from builders import build_inline_keyboard, build_inline_settings_keyboard, get_main_menu, get_settings
from database.session import async_session
from database.models import User, SentGame
from enums import DeviceSettingsButtons, MainMenuButtons, PlatformSettingsButtons, SettingsButtons, TypeSettingsButtons
from services.parser import GamerPowerAPI
from aiogram import F, Bot, Dispatcher, types
from aiogram.filters import Command

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
    return await message.answer("Проверяю раздачи...", reply_markup=get_main_menu())


# ------------------- Settings/Device -------------------

@dp.message(F.text == SettingsButtons.DEVICE.value)
async def device_settings_cmd(message: types.Message):
    return await message.answer("Выберите устройство", reply_markup=build_inline_settings_keyboard(
        user_settings={}, 
        category="device", 
        adjust=[2, 2, 2, 2]
    ))


@dp.callback_query(F.data == "device:pc")
async def pc_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали ПК")


@dp.callback_query(F.data == "device:ps4")
async def ps4_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали PlayStation 4")


@dp.callback_query(F.data == "device:ps5")
async def ps5_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали PlayStation 5") 


@dp.callback_query(F.data == "device:xbox")
async def xbox_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Xbox Series X/S")


@dp.callback_query(F.data == "device:xbox_one")
async def xbox_one_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Xbox One")


@dp.callback_query(F.data == "device:nintendo_switch")
async def nintendo_switch_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Nintendo Switch")


@dp.callback_query(F.data == "device:android")
async def android_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Android")


@dp.callback_query(F.data == "device:ios")
async def ios_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали iOS")


# ------------------- Settings/Platform -------------------

@dp.message(F.text == SettingsButtons.PLATFORM.value)
async def platform_settings_cmd(message: types.Message):
    return await message.answer("Выберите платформу", reply_markup=build_inline_settings_keyboard(
        user_settings={}, 
        category="platform", 
        adjust=[2, 2]
    ))    


@dp.callback_query(F.data == "platform:steam")
async def steam_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Steam")


@dp.callback_query(F.data == "platform:epic_games")
async def epic_games_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Epic Games")


@dp.callback_query(F.data == "platform:gog")
async def gog_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали GOG")


@dp.callback_query(F.data == "platform:itchio")
async def itchio_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Itch.io")


# ------------------- Settings/Type -------------------

@dp.message(F.text == SettingsButtons.TYPE.value)
async def type_settings_cmd(message: types.Message):
    return await message.answer("Выберите тип раздач", reply_markup=build_inline_settings_keyboard(
        user_settings={}, 
        category="type", 
        adjust=[1, 1, 1]))


@dp.callback_query(F.data == "type:early_access")
async def early_access_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Ранний доступ")


@dp.callback_query(F.data == "type:game")
async def game_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали Игру")


@dp.callback_query(F.data == "type:dlc")
async def dlc_settings_cmd(callback: types.CallbackQuery):
    return await callback.answer("Вы выбрали DLC")

# --------------------------------------

def get_giveaways_list(games):
    games_dict = {}
    for game in games:
        if not game["end_date"] or game["end_date"] == "N/A":
            continue
        games_dict[game["id"]] = {
            "title" : game["title"],
            "image" : game["image"],
            "end_date" : game["end_date"],
            "type" : game["type"],
            "open_giveaway_url" : game["open_giveaway_url"]
        }
    return games_dict


def get_games_msg(games_dict: dict):
    num = 0

    message = "Текущие раздачи: \n\n"
    for game in games_dict.values():
        num += 1
        message += f"{num}. {game['title']} ({game['type']}) – {game['open_giveaway_url']} до {game['end_date']}\n\n"

    return message


async def check_giveaways():
    while True:
        games = await GamerPowerAPI.get_giveaways(platform="pc")
        if not games:
            logger.info("New giveaways don't detected")
            await asyncio.sleep(40)  # Ждем 30 минут перед следующей проверкой 1800 sec
            continue

        user_ids = await get_active_users()
        games_list = get_giveaways_list(games=games)
        message = get_games_msg(games_dict=games_list)

        for uid in user_ids:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text=message
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