from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Literal, Optional, Union, TYPE_CHECKING
from datetime import datetime

# Local imports
from .abc import Postable, _purge_helper
from .errors import ClientException
from .utils import MISSING, parse_time

__all__ = [
	'Thread',
	'ThreadMember'
]

if TYPE_CHECKING:
	from typing_extensions import Self

	from .team import Team
	from .channel import TextChannel
	from .member import Member
	from .post import Post, PartialPost
	from .state import ConnectionState
	from .payloads.threads import Thread as ThreadPayload, ThreadMember as ThreadMemberPayload

class Thread(Postable, Hashable):
	"""Represents a Mattermost Thread"""

	__slots__ = (
		'id',
		'reply_count',
		'last_reply_at',
		'last_viewed_at',
		'participants',
		'post',
		'_state'
	)

	def __init__(self, *, team: Team, state: ConnectionState, data: ThreadPayload) -> None:
		self._state: ConnectionState = state
		self.team = team
		self._from_data(data)

	async def _get_channel(self) -> Self:
		return self

	def __repr__(self) -> str:
		return f'<Thread id={self.id}'

	def _from_data(self, data: ThreadPayload) -> None:
		self.id: str = data['id']
		self.reply_count: int = data['reply_count']
		self.last_reply_at: datetime = data['last_reply_at']
		self.last_viewed_at: datetime = data['last_viewed_at']
		self.participants: datetime = data['participants']
		self.post: datetime = data['post']
		
	def _update(self, data: ThreadPayload) -> None:
		...

	@property
	def parent(self) -> Optional[TextChannel]:
		...

	@property
	def mention(self) -> str:
		...
	
	@property
	def jump_url(self) -> str:
		...

	@property
	def starter_post(self) -> Optional[Post]:
		...

	@property
	def last_post(self) -> Optional[Post]:
		...

	async def delete_posts(self, posts: Iterable[str], /, *, reason: Optional[str] = None) -> None:
		...

	async def purge(
		self,
		*,
		limit: Optional[int] = 100,
		check: Callable[[Post], bool] = MISSING,
		before: Optional[datetime] = None,
		after: Optional[datetime] = None,
		around: Optional[datetime] = None,
		oldest_first: Optional[bool] = None,
		bulk: bool = True,
		reason: Optional[str] = None
	) -> List[Post]:
		...

	async def edit(
		self
	) -> Thread:
		# TODO: Not sure if editing a thread is a thing since they aren't named in mm
		...

	async def join(self) -> None:
		# TODO: I believe this is follow in mm
		...

	async def leave(self) -> None:
		# TODO: I believe this is unfollow
		...

	async def add_user(self, user: str, /) -> None:
		...

	async def remove_user(self, user: str, /) -> None:
		...

	async def fetch_member(self, user_id: str, /) -> None:
		...

	async def fetch_members(self) -> List[ThreadMember]:
		...

	async def delete(self) -> None:
		...

	def get_partial_post(self, post_id: str, /) -> PartialPost:
		...

	def _add_member(self, member: ThreadMember, /) -> None:
		...

	def _remove_member(self, member_id: str, /) -> None:
		...

class ThreadMember(Hashable):
	...