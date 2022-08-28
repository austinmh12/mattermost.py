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
from .http import handle_post_parameters
from .threads import Thread

__all__ = [
	'TextChannel',
	'DMChannel',
	'PartialPostable',
	'GroupChannel'
]

if TYPE_CHECKING:
	from typing_extensions import Self
	from .file import File
	from .state import ConnectionState
	from .user import ClientUser, User, BaseUser
	from .post import Post, PartialPost
	from .member import Member
	from .team import Team, TeamChannel as TeamChannelType

	OverwriteKeyT = TypeVar('OverwriteKeyT', BaseUser)

class ThreadWithPost(NamedTuple):
	thread: Thread
	post: Post

class TextChannel(mattermost.abc.Postable, mattermost.abc.TeamChannel, Hashable):
	__slots__ = (
		'name',
		'id',
		'team',
		'_state',
		'_overwrites',
		'_type',
		'_last_post_id'
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
	def last_post(self) -> Optional[Post]:
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

	async def delete_posts(self, posts: Iterable[str], *, reason: Optional[str] = None) -> None:
		...

	async def purge(
		self,
		*,
		limit: Optional[int] = 100,
		check: Callable[[Post], bool] = MISSING,
		before: Optional[datetime.datetime] = None,
		after: Optional[datetime.datetime] = None,
		around: Optional[datetime.datetime] = None,
		oldest_first: Optional[bool] = None,
		bulk: bool = True,
		reason: Optional[str] = None
	) -> List[Post]:
		...

	# Webhooks and following

	# Partial post stuff

	def get_thread(self, thread_id: str, /) -> Optional[Thread]:
		...

	async def create_thread(
		self,
		*,
		name: str,
		post: Optional[str] = None,
		reason: Optional[str] = None
	) -> Thread:
		...

class DMChannel(mattermost.abc.Postable, mattermost.abc.PrivateChannel, Hashable):
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
	def _from_post(cls, state: ConnectionState, channel_id: str) -> Self:
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

class GroupChannel(mattermost.abc.Postable, mattermost.abc.PrivateChannel, Hashable):
	...

	# permissions and partial posts
class PartialPostable(mattermost.abc.Postable, Hashable):
	def __init__(self, state: ConnectionState, id: str, team_id: Optional[str] = None, type: Optional[str] = None) -> None:
		self._state: ConnectionState = state
		self.id: str = id
		self.team_id: str = team_id
		self.type: str = type

	def __repr__(self) -> str:
		return ''

	async def _get_channel(self) -> PartialPostable:
		return self

	# TODO: Finish the rest of the skeleton

def _team_channel_factory(channel_type):
	...

def _channel_factory(channel_type):
	...

def _threaded_channel_factory(channel_type):
	...

def _threaded_team_channel_factory(channel_type):
	...