from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from enums import SETTINGS, MainMenuButtons, SettingsButtons


def build_reply_keyboard(list_of_buttons, adjust: list[int] = None, one_time_keyboard: bool = False):
    builder = ReplyKeyboardBuilder()
    for button in list_of_buttons:
        builder.button(text=button["text"])

    if adjust is not None:
        builder.adjust(*adjust)

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=one_time_keyboard)


def build_inline_keyboard(list_of_buttons, adjust: list[int] = None):
    inline_builder = InlineKeyboardBuilder()
    for button in list_of_buttons:
        inline_builder.button(text=button["text"], callback_data=button["callback_data"])

    if adjust is not None:
        inline_builder.adjust(*adjust)

    return inline_builder.as_markup()


def build_inline_settings_keyboard(user_settings: dict, category: str, adjust: list[int] = None):
    inline_builder = InlineKeyboardBuilder()

    current_category_items = SETTINGS[category]  # Получаем словарь с кнопками для текущей категории
    user_choices = user_settings.get(category, [])  # Получаем список выбранных пользователем значений для текущей категории

    for key, button in current_category_items.items():
        # Проверяем, выбрано ли текущее значение пользователем
        if key in user_choices:
            inline_builder.button(text=f"✅ {button['text']}", callback_data=button["callback_data"])
        else:
            inline_builder.button(text=f"❌ {button['text']}", callback_data=button["callback_data"])

    if adjust is not None:
        inline_builder.adjust(*adjust)

    return inline_builder.as_markup()


def get_main_menu():
        return build_reply_keyboard([
        {"text": MainMenuButtons.CHECK.value},
        {"text": MainMenuButtons.SETTINGS.value}
    ])


def get_settings(is_active: bool = True):
    return build_reply_keyboard([
        {"text": SettingsButtons.DEVICE.value},
        {"text": SettingsButtons.PLATFORM.value},
        {"text": SettingsButtons.TYPE.value},
        {"text": SettingsButtons.TIMEZONE.value},
        {"text": SettingsButtons.DEACTIVATE.value} if is_active else {"text": SettingsButtons.ACTIVATE.value},
        {"text": SettingsButtons.BACK.value}
    ], adjust=[3, 2, 1])


def get_timezone_keyboard(current_start: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Создаем 6 кнопок с часовыми поясами (например, от -1 до 4)
    for tz in range(current_start, current_start + 6):
        # Ограничиваем реальными поясами (от -12 до +14)
        if -12 <= tz <= 14:
            builder.button(text=f"{'+' if tz > 0 else ''}{tz}", callback_data=f"set_tz:{tz}")
    

    # Добавляем кнопки навигации (стрелки)
    nav_buttons = []
    # Если мы не в самом начале, показываем стрелку влево
    if current_start > -12:
        nav_buttons.append(builder.button(text="⬅️", callback_data=f"shift_tz:{current_start - 3}"))
    
    # Если не в самом конце, показываем стрелку вправо
    if current_start < 9:
        nav_buttons.append(builder.button(text="➡️", callback_data=f"shift_tz:{current_start + 3}"))

    builder.adjust(3, 3, 2)

    return builder.as_markup()