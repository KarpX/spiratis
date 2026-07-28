import httpx
import logging

logger = logging.getLogger(__name__)

class GamerPowerAPI:
    BASE_URL = "https://www.gamerpower.com/api/giveaways"

    @classmethod
    async def get_giveaways(cls, platform: str = "pc"):
        """
        Получает список раздач с GamerPower.
        :param platform: Платформа (pc, steam, epic-games-store, ubisoft, origin)
        :return: Список словарей с данными о играх или None в случае ошибки
        """
        params = {"platform": platform}
        
        try:
            # Используем тайм-аут 10 секунд, чтобы бот не завис, если API тормозит
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.BASE_URL, params=params)
                
                # Если всё ок, возвращаем данные
                if response.status_code == 200:
                    return response.json()
                
                # API GamerPower возвращает 404, если раздач по фильтру нет
                elif response.status_code == 404:
                    logger.info("Раздач на данный момент нет.")
                    return []
                
                else:
                    logger.error(f"Ошибка API: Статус {response.status_code}")
                    return None

        except httpx.ConnectError:
            logger.error("Ошибка подключения к серверу API.")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при запросе к API: {e}")
            return None

# Пример того, как данные выглядят внутри (для справки):
# [
#   {
#     "id": 123,
#     "title": "Ghostrunner",
#     "worth": "$29.99",
#     "image": "https://www.gamerpower.com/...",
#     "description": "Get it for free on Epic Games Store!",
#     "open_giveaway_url": "https://www.gamerpower.com/open/ghostrunner",
#     "platforms": "PC, Epic Games Store"
#   }
# ]