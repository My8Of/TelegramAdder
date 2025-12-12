import asyncio
import os
from datetime import datetime
from threading import Thread
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.src.api import TelegramManger
from app.utils.cache import save_users_cache
from app.utils.logger import ColorLogger
from app.utils.models import UserExportData

load_dotenv()

try:
    API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
except ValueError:
    API_ID = 0


API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER")
GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
TARGET_GROUP_ID = os.getenv("TELEGRAM_TARGET_GROUP_ID")

logger = ColorLogger("Main")
connector = TelegramManger(API_ID, API_HASH, PHONE_NUMBER, GROUP_ID)

LOGO = """
░▒▓███████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓█████████████▓▒░
"""


async def main():
    print(LOGO)  # O logo é impresso no logger, não no print.
    logger.info("Starting Telegram Scraper")

    try:
        if not all(
            [API_ID, API_HASH, PHONE_NUMBER, GROUP_ID, TARGET_GROUP_ID]
        ):  # TARGET_GROUP_ID também é obrigatório
            logger.error(
                "Por favor, configure as variáveis de ambiente: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE_NUMBER, TELEGRAM_GROUP_ID e TELEGRAM_TARGET_GROUP_ID."
            )

        # A lógica de raspagem deve ser executada
        async with connector as scraper:
            users_list: List[UserExportData] = await scraper.get_last_100_users()

            if users_list:
                logger.info(
                    f"Busca finalizada. Total de {len(users_list)} usuários únicos prontos para exportação/adição."
                )

            if not users_list:
                logger.warning("Nenhum usuário foi coletado.")

            file_name = (
                f"app/cache/users_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            )
            await save_users_cache(users_list=users_list, file_name=file_name)

            await connector.add_users_to_group(TARGET_GROUP_ID)

    except Exception as e:
        logger.critical(f"Falha na execução do scraper principal: {e}")


if __name__ == "__main__":
    asyncio.run(main())
