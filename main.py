import asyncio
import logging
import os
import sys
from sqlalchemy import select
from database.session import async_session
from database.models import User, SentGame
from services.parser import GamerPowerAPI
from aiogram import Bot, Dispatcher, types
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
    await message.answer("Привет! Я Spiratis. Я буду присылать тебе уведомления о бесплатных играх в Steam и других магазинах!")


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
        async with async_session() as session:
            user_ids = await get_active_users()
            games_list = get_giveaways_list(games=games)
            message = get_games_msg(games_dict=games_list)
            logger.info(message)
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