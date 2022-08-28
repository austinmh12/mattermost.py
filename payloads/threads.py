from __future__ import annotations
from typing import List, Optional, TypedDict

from .post import Post

class ThreadMember(TypedDict):
	id: str
	user_id: str

class Thread(TypedDict):
	id: str
	post_id: str
	channel_id: str