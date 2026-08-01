import asyncio
from datetime import datetime, timedelta
import logging
import os
import sys

from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from sqlalchemy import delete, select
from builders import build_inline_settings_keyboard, get_main_menu, get_settings, get_timezone_keyboard
from database.session import async_session
from database.models import User, SentGame
from enums import MAPPING, SETTINGS, MainMenuButtons, SettingsButtons
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


async def set_user_inactive(user_id: int):
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user.is_active = False
        await session.commit()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user_if_not_exists(message.from_user.id)
    text=(
        "🎮 <b>Добро пожаловать в Spiratis!</b> 🎮\n\n"
        "Я помогу тебе не пропустить бесплатные игры. Давай настроим фильтры, "
        "чтобы ты получал только то, что тебе интересно.\n\n"
        "Начнем с выбора <b>устройств</b>!"
    )
    
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        settings = user.settings if user else {}
        
    await message.answer(
        text=text,
        reply_markup=build_inline_settings_keyboard(settings, "device", [2, 2], next_step="platform", is_setup=True),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("next_step:"))
async def handle_next_step(callback: types.CallbackQuery):
    step = callback.data.split(":")[1]
    
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        settings = user.settings

    if step == "platform":
        await callback.message.edit_text(
            "🔌 Теперь выбери <b>платформы</b>:",
            reply_markup=build_inline_settings_keyboard(settings, "platform", [2, 2], next_step="type", is_setup=True),
            parse_mode="HTML"
        )
    
    elif step == "type":
        await callback.message.edit_text(
            "📦 Какой <b>тип раздач</b> тебя интересует?",
            reply_markup=build_inline_settings_keyboard(settings, "type", [1], next_step="timezone", is_setup=True),
            parse_mode="HTML"
        )
    
    elif step == "timezone":
        await callback.message.edit_text(
            "🕒 И последнее — твой <b>часовой пояс</b>, чтобы время окончания раздач было верным:",
            reply_markup=get_timezone_keyboard(user.timezone_offset, True),
            parse_mode="HTML",
        )

    elif step == "finish":
        await callback.message.edit_text(
        f"Поздравляю, настройка окончена! Ты всегда можешь изменить настройки по кнопке <b>{MainMenuButtons.SETTINGS.value}</b> и выключить автоматические уведомления",
        reply_markup=get_main_menu(),
        parse_mode="HTML",
        )
    
    await callback.answer()


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
    if games_list:
        await send_giveaways_to_user(bot=bot, uid=user_id, user=user, games_dict=games_list)
        await mark_games_as_sent(user_id=user_id, game_ids_with_dates=[(game, games_list[game]['end_date']) for game in games_list.keys()])
    else:
        await message.answer("На данный момент новых раздач нет. Попробуйте позже.")


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
    category, value, is_setup = callback.data.split(":")[1:]  # Разделяем данные колбэка на категорию и значение
    is_setup = is_setup == "1"

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

    next_steps = {"device": "platform", "platform": "type", "type": "timezone", "timezone" : "finish"}
    current_next_step = next_steps.get(category)

    # Отправляем обновленную клавиатуру с учетом новых настроек
    await callback.message.edit_reply_markup(
        reply_markup=build_inline_settings_keyboard(
            user_settings=user.settings,
            category=category,
            adjust=[2, 2] if category != "type" else [1, 1, 1],
            next_step=current_next_step,
            is_setup=is_setup
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
    _, new_start, is_setup = callback.data.split(":")
    
    # Просто обновляем клавиатуру на новую страницу
    await callback.message.edit_reply_markup(
        reply_markup=get_timezone_keyboard(int(new_start), is_setup=(is_setup == "1"))
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("set_tz:"))
async def set_timezone(callback: types.CallbackQuery):
    _, selected_tz, is_setup = callback.data.split(":")
    selected_tz = int(selected_tz)
    
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        user.timezone_offset = selected_tz # Сохраняем в БД
        await session.commit()
        
    await callback.answer(f"✅ Часовой пояс установлен: UTC{'+' if selected_tz > 0 else ''}{selected_tz}")

    if is_setup == "1":
        await callback.message.delete()
        await callback.message.answer(
            f"🥳 <b>Поздравляю, настройка окончена!</b>\n\n"
            f"Ты всегда можешь изменить параметры по кнопке <b>{MainMenuButtons.SETTINGS.value}</b>.\n"
            f"Удачной охоты за играми! 🕹",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    else:
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
    u_platforms = user_settings.get("platform", [])
    u_devices = user_settings.get("device", [])
    u_types = [t.lower() for t in user_settings.get("type", [])]

    all_known_stores = [s.lower() for s in MAPPING["platform"].values()]

    games_dict = {}
    
    for game in games:
        if not game["end_date"] or game["end_date"] == "N/A":
            continue

        api_platforms_str = game["platforms"].lower()
        api_type_str = game["type"].lower()

        if u_types and api_type_str not in u_types:
            continue

        passed = False

        if not u_platforms and not u_devices:
            passed = True
        else:
            game_stores = [s for s in all_known_stores if s in api_platforms_str]
            
            match_device = False
            if u_devices:
                device_search_terms = [MAPPING["device"].get(d, d) for d in u_devices]
                match_device = any(term in api_platforms_str for term in device_search_terms)

            match_platform = False
            if u_platforms:
                platform_search_terms = [MAPPING["platform"].get(p, p) for p in u_platforms]
                match_platform = any(term in api_platforms_str for term in platform_search_terms)

            # --- ЛОГИКА ПРИНЯТИЯ РЕШЕНИЯ ---
            
            if game_stores:
                # Если это игра из магазина (Steam, Epic и т.д.)
                if u_platforms:
                    # Если пользователь указал конкретные магазины — показываем только их
                    # Игнорируем совпадение по "PC", если магазин не тот
                    passed = match_platform
                else:
                    # Если пользователь НЕ выбирал магазины, но выбрал девайсы (например PC)
                    # Показываем все магазины для этого девайса
                    passed = match_device
            else:
                # Если у игры нет тега магазина (например, просто "Android" или "DRM-Free")
                # Используем логику "ИЛИ" (подошел или девайс, или платформа)
                passed = match_device or match_platform

        if not passed:
            continue

        async with async_session() as session:
            sent_game = await get_sent_game_to_user(user_id=uid, game_id=game["id"])
            if sent_game:
                continue

        games_dict[game["id"]] = {
            "title": game["title"],
            "image": game["image"],
            "platforms": game["platforms"],
            "end_date": game["end_date"],
            "type": game["type"],
            "open_giveaway_url": game["open_giveaway_url"]
        }
        
    return games_dict


async def mark_games_as_sent(user_id: int, game_ids_with_dates: list):
    async with async_session() as session:
        async with session.begin():
            for game_id, game_date in game_ids_with_dates:
                try:
                    date_end = datetime.strptime(game_date, "%Y-%m-%d %H:%M:%S")
                except:
                    date_end = None
                
                new_sent_game = SentGame(user_id=user_id, game_id=game_id, end_date=date_end)
                session.add(new_sent_game)
        await session.commit()


def get_games_msg(games_dict: dict, user: User, current_num: int = 0):
    num = current_num

    photos = []
    message = "🎁 <b>АКТУАЛЬНЫЕ РАЗДАЧИ ИГР</b> 🎁\n" 
    message += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
    for game in games_dict:
        num += 1

        title = game["title"]
        platforms = game["platforms"]
        g_type = game["type"]
        image = game["image"]
        game_link = game['open_giveaway_url']

        api_time = game['end_date']
        user_time = format_date_for_user(api_time, user.timezone_offset)

        photos.append(image)

        message += (
            f"{num}️. <b>{title}</b>\n"
            f"Тип: <code>{g_type}</code> | {platforms}\n"
            f"⏳ До: <b>{user_time}</b>\n"
            f"🔗 <a href='{game_link}'>ЗАБРАТЬ ИГРУ</a>\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        )

    if num == 0:
        message = None
    return (message, photos)


async def send_giveaways_to_user(bot: Bot, uid: int, user: User, games_dict: dict):
    if not games_dict:
        return

    all_games = list(games_dict.values())
    
    current_num = 0
    for chunk in chunk_list(all_games, 5):
        message_text, photos = get_games_msg(chunk, user, current_num)
        current_num += len(chunk)

        try:
            if len(photos) > 1:
                await bot.send_media_group(
                    chat_id=uid,
                    media=[types.InputMediaPhoto(
                        media=photo, 
                        caption=message_text if i == 0 else "",
                        parse_mode="HTML"
                    ) for i, photo in enumerate(photos)]
                )
            else:
                await bot.send_photo(
                    chat_id=uid,
                    photo=photos[0],
                    caption=message_text,
                    parse_mode="HTML"
                )
            await asyncio.sleep(0.5) 

        except TelegramForbiddenError:
            logger.info(f"Пользователь {uid} заблокировал бота")
            await set_user_inactive(uid)

        except TelegramNotFound:
            logger.warning(f"Чат с пользователем {uid} не найден. Деактивация...")
            await set_user_inactive(uid)
        
        except Exception as e:
            logger.error(f"Ошибка отправки пачки игр пользователю {uid}: {e}")
            if "ENTITY_BOUNDS_INVALID" in str(e) or "too long" in str(e).lower():
                 await bot.send_message(uid, message_text, parse_mode="HTML", disable_web_page_preview=True)


async def cleanup_old_sent_games():
    logger.info("Cleaning up old sent games...")

    threshold = datetime.now() - timedelta(days=1)
    
    async with async_session() as session:
        async with session.begin():
            query = delete(SentGame).where(SentGame.end_date < threshold)
            result = await session.execute(query)
            logger.info(f"Очистка завершена. Удалено записей: {result.rowcount}")
        await session.commit()


def chunk_list(lst, n):
    """Разбивает список на части по n элементов."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def check_giveaways():
    while True:
        logger.info("Checking giveaways...")
        games = await GamerPowerAPI.get_giveaways()
        if not games:
            logger.info("New giveaways don't detected")
            await asyncio.sleep(3600)
            return

        user_ids = await get_active_users()

        for uid in user_ids:
            async with async_session() as session:
                async with session.begin():
                    user = await session.get(User, uid)
                    if not user:
                        continue  # Если пользователь не найден, пропускаем его
                    
            games_list = await get_giveaways_list(games=games, user_settings=user.settings, uid=uid)
            if games_list:
                await send_giveaways_to_user(bot=bot, uid=uid, user=user, games_dict=games_list)
                await mark_games_as_sent(user_id=uid, game_ids_with_dates=[(game, games_list[game]['end_date']) for game in games_list.keys()])

        await asyncio.sleep(3600)


async def main():
    scheduler = AsyncIOScheduler()

    asyncio.create_task(check_giveaways())

    scheduler.add_job(cleanup_old_sent_games, CronTrigger(hour=6, minute=0))
    scheduler.start()

    await dp.start_polling(bot)
    logger.info("Bot has been started working...")

if __name__ == "__main__":
    asyncio.run(main())