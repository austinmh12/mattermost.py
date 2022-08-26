from __future__ import annotations

from typing import (
	Any,
	Callable,
	Dict,
	Iterable,
	List,
	Literal,
	Mapping,
	NamedTuple,
	Optional,
	TYPE_CHECKING,
	Sequence,
	Tuple,
	TypeVar,
	Union,
	overload
)

import datetime

# Local imports
import mattermost.abc
from . import utils
from .utils import MISSING
from .errors import ClientException
from .http import handle_message_parameters

__all__ = [
	'TextChannel',
	'DMChannel'
]

if TYPE_CHECKING:
	from typing_extensions import Self
	from .file import File
	from .state import ConnectionState
	from .user import ClientUser, User, BaseUser

	OverwriteKeyT = TypeVar('OverwriteKeyT', BaseUser)

class ThreadWithMessage(NamedTuple):
	thread: Thread
	message: Message

class TextChannel(mattermost.abc.Messageable, discord.abc.TeamChannel, Hashable):
	__slots__ = (
		'name',
		'id',
		'team',
		'_state',
		'_overwrites',
		'_type',
		'_last_message_id'
	)

	def __init__(self, *, state: ConnectionState, team: Team, data: TextChannelPayload) -> None:
		self._state: ConnectionState = state
		self.id: str = data['id']
		self._type: str = data['type']
		self._update(team, data)

	def __repr__(self) -> str:
		return ''

	def _update(self, team: Team, data: TextChannelPayload) -> None:
		...

	async def _get_channel(self) -> Self:
		return self

	@property
	def type(self) -> str:
		return self._type

	@property
	def members(self) -> List[Member]:
		...

	@property
	def threads(self) -> List[Thread]:
		...

	@property
	def last_message(self) -> Optional[Message]:
		...

	@overload
	async def edit(self) -> Optional[TextChannel]:
		...

	@overload
	async def edit(self, *, position: int, reason: Optional[str]) -> None:
		...

	@overload
	async def edit(
		self,
		*,
		reason: Optional[str],
		name: str = ...,
		topic: str = ...
	) -> TextChannel:
		...

	async def edit(self, *, reason: Optional[str] = None, **options: Any) -> Optional[TextChannel]:
		...

	# clone

	async def delete_messages(self, messages: Iterable[str], *, reason: Optional[str] = None) -> None:
		...

	async def purge(
		self,
		*,
		limit: Optional[int] = 100,
		check: Callable[[Message], bool] = MISSING,
		before: Optional[datetime.datetime] = None,
		after: Optional[datetime.datetime] = None,
		around: Optional[datetime.datetime] = None,
		oldest_first: Optional[bool] = None,
		bulk: bool = True,
		reason: Optional[str] = None
	) -> List[Message]:
		...

	# Webhooks and following

	# Partial message stuff

	def get_thread(self, thread_id: str, /) -> Optional[Thread]:
		...

	async def create_thread(
		self,
		*,
		name: str,
		message: Optional[str] = None,
		reason: Optional[str] = None
	) -> Thread:
		...

class DMChannel(mattermost.abc.Messageable, discord.abc.PrivateChannel, Hashable):
	__slots__ = ('id', 'recipient', 'me', '_state')

	def __init__(self, *, me: ClientUser, state: ConnectionState, data: DMChannelPayload):
		self._state: ConnectionState = state
		self.recipient: Optional[User] = state.store_user(data['recipients'][0]) # TODO: Look at the mm api for DMs
		self.me: ClientUser = me
		self.id: str = data['id']

	async def _get_channel(self) -> Self:
		return self

	def __str__(self) -> str:
		return ''

	def __repr__(self) -> str:
		return ''

	@classmethod
	def _from_message(cls, state: ConnectionState, channel_id: str) -> Self:
		...

	@property
	def type(self) -> str:
		...

	@property
	def team(self) -> Optional[Team]:
		return None

	@property
	def created_at(self) -> datetime.datetime:
		...

	# permissions and partial messages