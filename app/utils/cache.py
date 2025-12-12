import json
import os
from typing import List

from app.utils.logger import ColorLogger
from app.utils.models import UserExportData

logger = ColorLogger("cache")

FILE_NAME = "app/cache/users.json"


async def save_users_cache(users_list: List[UserExportData], file_name: str):
    """
    Salva a lista de usuários coletados em um arquivo JSON.
    Esta função sobrescreve o arquivo existente para fins de cache temporário.
    """

    # 1. Checa se o arquivo existe e avisa que está sobrescrevendo
    if os.path.exists(file_name):
        logger.warning(f"Sobrescrevendo cache temporário: {file_name}")

    # 2. Salva a lista completa no arquivo
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            # Mantemos o indent=4 para facilitar a inspeção visual em DEV
            json.dump(users_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.critical(f"Falha ao escrever no arquivo de cache {file_name}: {e}")
