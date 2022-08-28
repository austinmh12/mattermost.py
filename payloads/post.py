from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Union
from typing_extensions import NotRequired
from datetime import datetime

from .member import Member, UserWithMember
from .user import User
from .channel import Channel

class PartialPost(TypedDict):
	channel_id: str
	team_id: NotRequired[str]

class Attachment(TypedDict):
	id: str
	user_id: str
	post_id: str
	create_at: datetime
	update_at: datetime
	delete_at: datetime
	name: str
	extenstion: str
	size: int
	mime_type: str
	width: int
	height: int
	has_preview_image: bool

class Post(PartialPost):
	id: str
	create_at: datetime
	update_at: datetime
	delete_at: datetime
	props: Dict[str, Any]
	hashtag: str
	message: str