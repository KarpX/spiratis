import asyncio
from asyncio.log import logger
import os
from sqlalchemy import select
from database.session import async_session
from database.models import User, SentGame
from services.parser import GamerPowerAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

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
        result = await session.execute(select(SentGame.id).where(SentGame.user_id == user_id and SentGame.game_id == game_id))
        return result.scalars().first()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user_if_not_exists(message.from_user.id)
    await message.answer("Привет! Я Spiratis. Я буду присылать тебе уведомления о бесплатных играх в Steam и других магазинах!")


async def check_giveaways():
    while True:
        games = await GamerPowerAPI.get_giveaways(platform="pc")
        if not games:
            logger.info("New giveaways don't detected")
            await asyncio.sleep(40)  # Ждем 30 минут перед следующей проверкой 1800 sec
            continue
        async with async_session() as session:
            for game in games:                
                user_ids = await get_active_users()
                for uid in user_ids:
                    sent_game = await get_sent_game_to_user(user_id=uid, game_id=game["id"])
                    if sent_game:
                        logger.info(f"Game {game['id']} has already sent to user {uid}")
                        continue
                    try:
                        await bot.send_photo(
                            uid, 
                            photo=game['image'], 
                            caption=f"🎁 <b>{game['title']}</b>\n\n{game['open_giveaway_url']}",
                            parse_mode="HTML"
                        )
                        # Сохраняем игру
                        session.add(SentGame(id=game['id'], user_id=uid, game_id=game['id'], sent_at=str(asyncio.get_event_loop().time())))
                    except Exception:
                        pass # Тут можно помечать user.is_active = False если бот заблокирован
                
            await session.commit()
        await asyncio.sleep(40)

async def main():
    await check_giveaways()  # Запускаем проверку раздач в фоне
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())