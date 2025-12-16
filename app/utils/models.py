from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# Definição do tipo de retorno do usuário
UserExportData = Dict[str, Any]


class dbUser(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_bot: bool


class Users(BaseModel):
    id: int
    is_self: bool
    contact: bool
    mutual_contact: bool
    deleted: bool
    bot: bool
    bot_chat_history: bool
    bot_nochats: bool
    verified: bool
    restricted: bool
    min: bool
    bot_inline_geo: bool
    support: bool
    scam: bool
    apply_min_photo: bool
    fake: bool
    bot_attach_menu: bool
    premium: bool
    attach_menu_enabled: bool
    bot_can_edit: bool
    close_friend: bool
    stories_hidden: bool
    stories_unavailable: bool
    contact_require_premium: bool
    bot_business: bool
    bot_has_main_app: bool
    bot_forum_view: bool
    access_hash: int
    first_name: str
    last_name: Optional[str]
    username: str
    phone: str
    photo: Optional[Any]
    status: Any
    bot_info_version: Optional[int]
    restriction_reason: List[Any]
    bot_inline_placeholder: Optional[str]
    lang_code: Optional[str]
    emoji_status: Optional[Any]
    usernames: List[str]
    stories_max_id: Optional[int]
    color: Optional[str]
    profile_color: Optional[str]
    bot_active_users: Optional[int]
    bot_verification_icon: Optional[str]
    send_paid_messages_stars: Optional[int]
