from typing import List, Literal, Optional, TypedDict
from typing_extensions import NotRequired
from datetime import datetime

from .channel import TeamChannel
from .member import Member
from .user import User
from .threads import Thread

class UnavailableTeam(TypedDict):
	id: str
	unavailable: NotRequired[bool]

class Team(TypedDict):
	id: str
	create_at: datetime
	update_at: datetime
	delete_at: datetime
	display_name: str
	name: str
	description: str
	email: str
	type: str
	allowed_domains: str
	invite_id: str
	allow_open_invite: bool
	policy_id: str