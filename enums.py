from enum import Enum


class MainMenuButtons(Enum):
    CHECK = "🔍 Проверить"
    SETTINGS = "⚙️ Настройки"


class SettingsButtons(Enum):
    DEVICE = "📱 Устройство"
    PLATFORM = "🎮 Платформа"
    TYPE = "📁 Тип"
    DEACTIVATE = "❌ Выключить"
    BACK = "🔙 Назад"


class TypeSettingsButtons(Enum):
    EARLY_ACCESS = {"text": "Ранний доступ", "callback_data": "toggle:type:early_access"}
    GAME = {"text": "Игра", "callback_data": "toggle:type:game"}
    DLC = {"text": "DLC", "callback_data": "toggle:type:dlc"}


class DeviceSettingsButtons(Enum):
    PC = {"text": "ПК", "callback_data": "toggle:device:pc"}
    PS4 = {"text": "PS 4", "callback_data": "toggle:device:ps4"}
    PS5 = {"text": "PS 5", "callback_data": "toggle:device:ps5"}
    XBOX = {"text": "Xbox Series X/S", "callback_data": "toggle:device:xbox"}
    XBOX_ONE = {"text": "Xbox One", "callback_data": "toggle:device:xbox_one"}
    NINTENDO_SWITCH = {"text": "Nintendo Switch", "callback_data": "toggle:device:nintendo_switch"}
    ANDROID = {"text": "Android", "callback_data": "toggle:device:android"}
    IOS = {"text": "iOS", "callback_data": "toggle:device:ios"}


class PlatformSettingsButtons(Enum):
    STEAM = {"text": "Steam", "callback_data": "toggle:platform:steam"}
    EPIC_GAMES = {"text": "Epic Games", "callback_data": "toggle:platform:epic_games"}
    GOG = {"text": "GOG", "callback_data": "toggle:platform:gog"}
    # ITCHIO = {"text": "itch.io", "callback_data": "toggle:platform:itchio"}


SETTINGS ={
    "platform" : {
        "steam": PlatformSettingsButtons.STEAM.value,
        "epic_games": PlatformSettingsButtons.EPIC_GAMES.value,
        "gog": PlatformSettingsButtons.GOG.value,
        # "itchio": PlatformSettingsButtons.ITCHIO.value
    },
    "type" : {
        "early_access": TypeSettingsButtons.EARLY_ACCESS.value,
        "game": TypeSettingsButtons.GAME.value,
        "dlc": TypeSettingsButtons.DLC.value
    },
    "device" : {
        "pc": DeviceSettingsButtons.PC.value,
        "ps4": DeviceSettingsButtons.PS4.value,
        "ps5": DeviceSettingsButtons.PS5.value,
        "xbox": DeviceSettingsButtons.XBOX.value,
        "xbox_one": DeviceSettingsButtons.XBOX_ONE.value,
        "nintendo_switch": DeviceSettingsButtons.NINTENDO_SWITCH.value,
        "android": DeviceSettingsButtons.ANDROID.value,
        "ios": DeviceSettingsButtons.IOS.value
    }
}
