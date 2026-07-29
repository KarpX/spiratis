from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from enums import SETTINGS, DeviceSettingsButtons, MainMenuButtons, PlatformSettingsButtons, SettingsButtons, TypeSettingsButtons


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
            # Если выбрано, добавляем кнопку с галочкой
            inline_builder.button(text=f"✅ {button['text']}", callback_data=button["callback_data"])
        else:
            # Если не выбрано, добавляем обычную кнопку
            inline_builder.button(text=f"❌ {button['text']}", callback_data=button["callback_data"])

    if adjust is not None:
        inline_builder.adjust(*adjust)

    return inline_builder.as_markup()


def get_main_menu():
        return build_reply_keyboard([
        {"text": MainMenuButtons.CHECK.value},
        {"text": MainMenuButtons.SETTINGS.value}
    ])


def get_settings():
    return build_reply_keyboard([
        {"text": SettingsButtons.DEVICE.value},
        {"text": SettingsButtons.PLATFORM.value},
        {"text": SettingsButtons.TYPE.value},
        {"text": SettingsButtons.BACK.value}
    ], adjust=[2, 2])


# def get_device_settings():
#     return build_reply_keyboard([
#         {"text": DeviceSettingsButtons.PC.value},
#         {"text": DeviceSettingsButtons.PS4.value},
#         {"text": DeviceSettingsButtons.PS5.value},
#         {"text": DeviceSettingsButtons.XBOX.value},
#         {"text": DeviceSettingsButtons.XBOX_ONE.value},
#         {"text": DeviceSettingsButtons.NINTENDO_SWITCH.value},
#         {"text": DeviceSettingsButtons.ANDROID.value},
#         {"text": DeviceSettingsButtons.IOS.value}
#     ], adjust=[3, 3, 2])


# def get_platform_settings():
#     return build_reply_keyboard([
#         {"text": PlatformSettingsButtons.STEAM.value},
#         {"text": PlatformSettingsButtons.EPIC_GAMES.value},
#         {"text": PlatformSettingsButtons.GOG.value},
#         {"text": PlatformSettingsButtons.ITCHIO.value}
#     ], adjust=[2, 2])


# def get_type_settings():
#     return build_reply_keyboard([
#         {"text": TypeSettingsButtons.EARLY_ACCESS.value},
#         {"text": TypeSettingsButtons.GAME.value},
#         {"text": TypeSettingsButtons.DLC.value}
#     ], adjust=[3])
