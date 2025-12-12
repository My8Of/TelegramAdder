from typing import Any, Dict

from pydantic import BaseModel

# Definição do tipo de retorno do usuário
UserExportData = Dict[str, Any]


class User(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    is_bot: bool
