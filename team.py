from __future__ import annotations

import copy
from datetime import datetime
import unicodedata
from typing import (
	TYPE_CHECKING,
	Any,
	AsyncIterator,
	ClassVar,
	Collection,
	Coroutine,
	Dict,
	List,
	Optional,
	Sequence,
	Set,
	Union
)

# Local imports
from . import utils, abc
from .member import Member
from .errors import InvalidData
from .channel import *
from .channel import _team_channel_factory, _threaded_team_channel_factory
from .user import User
from .threads import Thread, ThreadMember
from .file import File

__all__ = [
	'Guild'
]

MISSING = utils.MISSING

if TYPE_CHECKING:
	from .channel import TextChannel
	from .state import ConnectionState
	from .payloads.team import Team as TeamPayload, TeamChannel as TeamChannelPayload

	TeamChannel = TextChannel

class Team(Hashable):
	"""Represents a Mattermost team."""

	__slots__ = (
		'id',
		'create_at',
		'update_at',
		'delete_at',
		'display_name',
		'name',
		'description',
		'email',
		'type',
		'allowed_domains',
		'invite_id',
		'allow_open_invite',
		'policy_id'
	)

	def __init__(self, *, data: TeamPayload, state: ConnectionState) -> None:
		self._channels: Dict[str, TeamChannel] = {}
		self._members: Dict[str, Member] = {}
		self._threads: Dict[str, Thread] = {}
		self._state: ConnectionState = state
		self._member_count: Optional[int] = None
		self._from_data(data)

	def _add_channel(self, channel: TeamChannel, /) -> None:
		...

	def _remove_channel(self, channel: TeamChannel, /) -> None:
		...

	def _add_member(self, member: Member, /) -> None:
		...

	def _remove_member(self, member: str, /) -> None:
		...

	def _add_thread(self, thread: Thread, /) -> None:
		...

	def _remove_thread(self, thread: str, /) -> None:
		...

	def _clear_threads(self) -> None:
		...

	def _remove_threads_by_channel(self, channel_id: str) -> None:
		...

	def _filter_threads(self, channel_ids: Set[str]) -> Dict[str, Thread]:
		...

	def __str__(self) -> str:
		return self.name or ''

	def __repr__(self) -> str:
		return f'<Team id={self.id} name={self.name}>'

	@classmethod
	def _create_unavailable(cls, *, state: ConnectionState, team_id: str) -> Team:
		return cls(state=state, data={'id': team_id, 'unavailable': True})

	def _from_data(self, team: TeamPayload) -> None:
		self.name: str = team['name']
		self.create_at: datetime = team['create_at']
		self.update_at: datetime = team['update_at']
		self.delete_at: datetime = team['delete_at']
		self.display_name: str = team['display_name']
		self.id: str = team['id']
		self.description: str = team['description']
		self.email: str = team['email']
		self.type: str = team['type']
		self.allowed_domains: str = team['allowed_domains']
		self.invite_id: str = team['invite_id']
		self.allow_open_invite: bool = team['allow_open_invite']
		self.policy_id: str = team['policy_id']

	@property
	def channels(self) -> Sequence[TeamChannel]:
		...

	@property
	def threads(self) -> Sequence[Thread]:
		...

	@property
	def me(self) -> Member:
		...

	@property
	def text_channels(self) -> List[TextChannel]:
		...

	def _resolve_channel(self, id: Optional[str], /) -> Optional[Union[TeamChannel, Thread]]:
		...

	def get_channel_or_thread(self, channel_id: str, /) -> Optional[Union[Thread, TeamChannel]]:
		...

	def get_channel(self, channel_id: str, /) -> Optional[TeamChannel]:
		...

	def get_thread(self, thread_id: str, /) -> Optional[Thread]:
		...

	@property
	def members(self) -> Sequence[Member]:
		...

	def get_member(self, user_id: str, /) -> Optional[Member]:
		...

	def get_member_named(self, name: str, /) -> Optional[Member]:
		...

	def _create_channel(
		self,
		name: str,
		**options: Any
	) -> Coroutine[Any, Any, TeamChannelPayload]:
		...

	async def create_text_channel(
		self,
		name: str,
		*,
		reason: Optional[str] = None
	) -> TextChannel:
		...

	async def leave(self) -> None:
		"""Leaves the team"""
		...

	async def delete(self) -> None:
		"""Deletes the team"""

	async def edit(
		self,
		*,
		name: str = MISSING,
		description: Optional[str] = MISSING
	) -> Team:
		...

	async def fetch_channels(self) -> Sequence[TeamChannel]:
		...

	async def active_threads(self) -> List[Thread]:
		...

	async def fetch_members(self, *, limit: Optional[int] = 1000, after: datetime = MISSING) -> AsyncIterator[Member]:
		...

	async def fetch_member(self, member_id: str, /) -> Member:
		...

	async def fetch_channel(self, channel_id: str, /) -> Union[TeamChannel, Thread]:
		...

	async def fetch_emojies(self):
		...

	async def fetch_emoji(self, emoji, /):
		...

	async def create_custom_emoji(self, *, name: str, image: bytes):
		...

	async def delete_emoji(self, emoji, /) -> None:
		...