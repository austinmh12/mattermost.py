from __future__ import annotations

import copy
import time
import asyncio
from datetime import datetime
from typing import (
	TYPE_CHECKING,
	Any,
	AsyncIterator,
	Callable,
	Iterable,
	Optional,
	Protocol,
	Sequence,
	Union,
	overload,
	runtime_checkable
)

from .errors import ClientException
from .file import File
from .http import handle_post_parameters
from . import utils

__all__ = (
	'User',
	'PrivateChannel',
	'TeamChannel',
	'Postable'
)

if TYPE_CHECKING:
	from typing_extensions import Self

	from .client import Client
	from .user import ClientUser
	from .state import ConnectionState
	from .channel import TextChannel, DMChannel, PartialPostable
	from .team import Team
	from .post import Post, PostReference, PartialPost
	from .threads import Thread

	PartialPostableChannel = Union[TextChannel, Thread, DMChannel, PartialPostable]
	# PostableChannel = Union[PartialPostableChannel, GroupChannel]

MISSING = utils.MISSING

class _Undefined:
	def __repr__(self) -> str:
		return 'see-below'

_undefined: Any = _Undefined()

async def _single_delete_strategy(posts: Iterable[Post], *, reason: Optional[str] = None) -> None:
	for p in posts:
		await p.delete()

async def _purge_helper() -> List[Post]:
	...

@runtime_checkable
class User(Protocol):
	name: str
	bot: bool
	system: bool

	@property
	def display_name(self) -> str:
		raise NotImplementedError

	@property
	def mention(self) -> str:
		raise NotImplementedError

	@property
	def avatar(self) -> str:
		raise NotImplementedError

	def mentioned_in(self, post: Post) -> bool:
		raise NotImplementedError

class PrivateChannel:
	__slots__ = ()

	id: str
	me: ClientUser

class TeamChannel:
	__slots__ = ()

	id: str
	name: str
	team: Team
	type: str
	_state: ConnectionState

	if TYPE_CHECKING:
		def __init__(self, *, state: ConnectionState, team: Team, data: TeamChannelPayload) -> None:
			...

	def __str__(self) -> str:
		return self.name

	def _update(self, team: Team, data: Dict[str, Any]) -> None:
		raise NotImplementedError

	async def _edit():
		...

	@property
	def mention(self) -> str:
		...

	@property
	def created_at(self) -> datetime:
		...

	async def delete(self, *, reason: Optional[str]) -> None:
		...

	# Stuff for permissions and invites

class Postable:
	__slots__ = ()
	_state: ConnectionState

	async def _get_channel(self) -> PostableChannel:
		raise NotImplementedError

	@overload
	async def send(
		self,
		content: Optional[str] = ...,
		*,
		tts: bool = ..., # TODO: Does mm has tts?
		file: File = ...,
		delete_after: float = ...,
		reference: Union[Post, PostReference, PartialPost] = ...,
		mention_author: bool = ...,
	) -> Post:
		...

	@overload
	async def send(
		self,
		content: Optional[str] = ...,
		*,
		tts: bool = ..., # TODO: Does mm has tts?
		files: Sequence[File] = ...,
		delete_after: float = ...,
		reference: Union[Post, PostReference, PartialPost] = ...,
		mention_author: bool = ...,
	) -> Post:
		...

	async def send(
		self,
		content: Optional[str] = None,
		*,
		tts: bool = False,
		file: Optional[File] = None,
		files: Optional[Sequence[File]] = None,
		delete_after: Optional[float] = None,
		reference: Optional[Union[Post, PostReference, PartialPost]] = None,
		mention_author: Optional[bool] = None
	) -> Post:
		...

	# TODO: Typing, will implement later

	async def fetch_post(self, id: str, /) -> Post:
		...

	async def pins(self) -> List[Post]:
		...

	async def history(
		self,
		*,
		limit: Optional[int] = 100,
		before: Optional[datetime] = None,
		after: Optional[datetime] = None,
		around: Optional[datetime] = None,
		oldest_first: Optional[bool] = None
	) -> AsyncIterator[Post]:
		...
