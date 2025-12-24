from datetime import datetime
from typing import Dict, List, Optional

import mysql.connector
from mysql.connector import Error

from app.utils.logger import ColorLogger
from app.utils.models import UserExportData, Users, dbUser

logger = ColorLogger("TelegramDatabase")


class TelegramDatabase:
    """Gerenciador de banco de dados para Telegram scraping"""

    def __init__(self, host, user, password, database):
        self.connection = None
        self.cursor = None
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connect()

    def connect(self):
        """Estabelece conexão com o banco de dados"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
            )
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("✅ Conectado ao banco de dados")
            # Auto-cria tabelas se não existirem
            return True
        except Error as e:
            logger.error(f"❌ Erro ao conectar ao banco: {e}")
            return False

    async def save_user(self, user: dbUser):
        """Salva um usuário no banco de dados"""

        try:
            self.cursor.execute(
                """
                INSERT IGNORE INTO users (id, username, first_name, last_name, is_bot)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    user.id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.is_bot,
                ),
            )
            self.connection.commit()
            logger.info(f"✅ Usuário {user.id} salvo com sucesso")
        except Error as e:
            logger.error(f"❌ Erro ao salvar usuário {user.id}: {e}")
        return True

    async def get_users(self, limit: int = 100) -> List[int]:
        """Retorna todos os usuários do banco de dados já adicionados do banco de dados"""
        try:
            self.cursor.execute(f"SELECT id FROM users WHERE added is not NULL")
            users = self.cursor.fetchall()
            logger.info(f"✅ {len(users)} usuários retornados com sucesso")
            ids = []
            for user in users:
                ids.append(int(user["id"]))
            return ids
        except Error as e:
            logger.error(f"❌ Erro ao buscar usuários: {e}")
            return []

    async def check_users(self, users: List[int]) -> None:
        try:
            # The 'user' parameter is the ID of the user to update.
            # The 'mysql.connector' expects parameters for execute to be a list, tuple, or dict.
            # So, wrap the single integer ID in a tuple.
            sql = "UPDATE users SET added = True WHERE id = %s"
            params = [(user,) for user in users]  # Pass the user ID as a tuple

            self.cursor.executemany(sql, params)
            self.connection.commit()
            logger.info(
                f"✅ Coluna 'added' dos usuários {users} atualizada para 'True' com sucesso."
            )
        except Error as e:
            logger.error(f"❌ Erro ao atualizar coluna 'added' do usuário {user}: {e}")
