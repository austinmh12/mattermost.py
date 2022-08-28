from typing import List, Literal, Optional, TypedDict, Union
from typing_extensions import NotRequired
from datetime import datetime

from .user import PartialUser
from .threads import ThreadMember

class _BaseChannel(TypedDict):
	id: str
	name: str

class _BaseTeamChannel(TypedDict):
	team_id: str

class PartialChannel(_BaseChannel):
	type: str

class _BaseTextChannel(_BaseTeamChannel, total=False):
	last_post_at: datetime

class TextChannel(_BaseTextChannel):
	...

class ThreadChannel(_BaseChannel):
	type: str
	parent_id: str
	last_post_at: datetime

TeamChannel = Union[TextChannel, ThreadChannel]

class DMChannel(_BaseChannel):
	recipients: List[PartialUser]

Channel = Union[TeamChannel, DMChannel]