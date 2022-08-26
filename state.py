from __future__ import annotations

import asyncio
from collections import deque, OrderedDict
import copy
import logging
from typing import (
	Callable,
	Coroutine,
	Deque,
	Dict,
	List,
	Optional,
	TYPE_CHECKING,
	Any,
	Sequence,
	TypeVar,
	Union
)
import weakref
import inspect
import os

from .enums import Status
# from .mentions import AllowedMentions

# Local imports
from . import utils


if TYPE_CHECKING:
	from .client import Client
	from .gateway import MattermostWebSocket
	from .http import HTTPClient

	T = TypeVar('T')

class ChunkRequest:
	def __init__(
		self,
		team_id: str,
		loop: asyncio.AbstractEventLoop,
		resolver: Callable[[str], Any],
		*,
		cache: bool = True
	) -> None:
		self.team_id: str = team_id
		self.resolver: Callable[[str], Any] = resolver
		self.loop: asyncio.AbstractEventLoop = loop
		self.cache: bool = cache
		self.nonce: str = os.urandom(16).hex() # Need to figure out what nonce is
		self.buffer: List[Member] = []
		self.waiters: List[asyncio.Future[List[Member]]] = []

	def add_members(self, members: List[Member]) -> None:
		self.buffer.extend(members)
		if self.cache:
			team = self.resolver(self.team_id)
			if team is None:
				return
			
			for member in members:
				existing = team.get_member(member.id)
				if existing is None or existing.joined_at is None:
					team._add_member(member)

	async def wait(self) -> List[Member]:
		future = self.loop.create_future()
		self.waiters.append(future)
		try:
			return await future
		finally:
			self.waiters.remove(future)

	def get_future(self) -> asyncio.Future[List[Member]]:
		future = self.loop.create_future()
		self.waiters.append(future)
		return future

	def done(self) -> None:
		for future in self.waiters:
			if not future.done():
				future.set_result(self.buffer)

_log = logging.getLogger(__name__)

async def logging_coroutine(coroutine: Coroutine[Any, Any, T], *, info: str) -> Optional[T]:
	try:
		await coroutine
	except Exception:
		_log.exception(f'Exception occurred during {info}')

class ConnectionState:
	if TYPE_CHECKING:
		_get_websocket: Callable[..., MattermostWebSocket]
		_get_client: Callable[..., Client]
		_parsers: Dict[str, Callable[[Dict[str, Any]], None]]

	def __init__(
		self,
		*,
		dispatch: Callable[..., Any],
		handlers: Dict[str, Callable[..., Any]],
		hooks: Dict[str, Callable[..., Coroutine[Any, Any, Any]]],
		http: HTTPClient,
		**options: Any
	) -> None:
		# Set after client.login
		self.loop: asyncio.AbstractEventLoop = utils.MISSING
		self.http: HTTPClient = http
		self.max_messages: Optional[int] = options.get('max_messages', 1000)
		if self.max_messages is not None and self.max_messages <= 0:
			self.max_messages = 1000
		self.dispatch: Callable[..., Any] = dispatch
		self.handlers: Dict[str, Callable[..., Any]] = handlers
		self.hooks: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = hooks
		self._ready_task: Optional[asyncio.Task] = None
		# self.application_id: Optional[int] = None
		# self.application_flags: ApplicationFlags = utils.MISSING
		self.heartbeat_timeout: float = options.get('heartbeat_timeout', 60.0)
		self.team_ready_timeout: float = options.get('team_ready_timeout', 2.0)
		if self.team_ready_timeout < 0:
			raise ValueError('team_ready_timeout cannot be negative')
		
		# allowed_mentions = options.get('allowed_mentions')
		# if allowed_mentions is not None and not isinstance(allowed_mentions, AllowedMentions):
		# 	raise TypeError('allowed_mentions parameter must be AllowedMentions')

		# self.allowed_mentions: Optional[AllowedMentions] = allowed_mentions
		self._chunk_requests: Dict[Union[int, str], ChunkRequest] = {}

		# activity = options.get('activity', None)
		# if activity:
		# 	if not isinstance(activity, BaseActivity):
		# 		raise TypeError('activity parameter must derive from BaseActivity')

		# 	activity = activity.to_dict()

		status = options.get('status', None)
		if status:
			status = str(status)

		# self._chunk_teams: bool = options.get()
		# Theres intent stuff here but I don't think mm needs it. Intents are discord specific
		
		# self._activity: Optional[ActivityPayload] = activity
		self._status: Optional[str] = status
		self._command_tree: Optional[CommandTree] = None
		self._translator: Optional[Translator] = None # Need to figure out what this is and if it's needed

		self.parsers: Dict[str, Callable[[Any], None]]
		self.parsers = parsers = {}
		for attr, func in inspect.getmembers(self):
			if attr.startswith('parse_'):
				parsers[attr[6:].upper()] = func

		self.clear()

	async def close(self) -> None:
		# This exists primarily to disconnect from voice clients but I'm not going to implement that yet
		if self._translator:
			await self._translator.unload()

	def clear(self, *, views: bool = True) -> None:
		self.user: Optional[ClientUser] = None
		self._users: weakref.WeakValueDictionary[str, User] = weakref.WeakValueDictionary()
		# self._emojis: Dict[int, Emoji] = {}
		# self._stickers: Dict[int, GuildSticker] = {}
		self._teams: Dict[str, Team] = {} # Teams are equivalent of Discord Guilds and have a str id instead of an int
		if views:
			...
			# self._view_store: ViewStore = ViewStore(self)
		self._private_channels: OrderedDict[int, PrivateChannel] = OrderedDict()
		self._private_channel_by_user: Dict[int, DMChannel] = {}
		if self.max_messages is not None:
			self._messages: Optional[Deque[Message]] = deque(maxlen=self.max_messages)
		else:
			self._messages: Optional[Deque[Message]] = None

	def process_chunk_requests(
		self,
		team_id: str,
		nonce: Optional[str],
		members: List[Member],
		complete: bool
	) -> None:
		removed = []
		for key, request in self._chunk_requests.items():
			if request.team_id == team_id and request.nonce == nonce:
				request.add_members(members)
				if complete:
					request.done()
					removed.append(key)

		for key in removed:
			del self._chunk_requests[key]

	def call_handlers(self, key: str, *args: Any, **kwargs: Any) -> None:
		try:
			func = self.handlers[key]
		except KeyError:
			pass
		else:
			func(*args, **kwargs)

	async def call_hooks(self, key: str, *args: Any, **kwargs: Any) -> None:
		try:
			coro = self.hooks[key]
		except KeyError:
			pass
		else:
			await coro(*args, **kwargs)

	@property
	def self_id(self) -> Optional[int]:
		u = self.user
		return u.id if u else None

	# Intents property
	
	# Voice client property and functions

	# Storing/Caching functions
	def store_user(self, data: Union[UserPayload, PartialUserPayload]) -> User:
		# Supposidly this is 4x faster than dict.setdefault
		user_id = str(data['id'])
		try:
			return self._users[user_id]
		except KeyError:
			user = User(state=self, data=data)
			self._users[user_id] = user
			return user

	def create_user(self, data: Union[UserPayload, PartialUserPayload]) -> User:
		return User(state=self, data=data)

	def get_user(self, id: str) -> Optional[User]:
		return self._users.get(id)

	# Storing emojis, stickers, and views

	@property
	def teams(self) -> Sequence[Team]:
		return utils.SequenceProxy(self._teams.values())

	def _get_team(self, team_id: Optional[str]) -> Optional[Team]:
		return self._teams.get(team_id)

	def _get_or_create_unavailable_team(self, team_id: str) -> Team:
		return self._teams.get(team_id) or Team._create_unavailable(state=self, team_id=team_id)

	def _add_team(self, team: Team) -> None:
		self._teams[team.id] = team

	def _remove_team(self, team: Team) -> None:
		self._teams.pop(team.id, None)

		# Remove the emojis and stickers for those guilds

		del team

	# Emoji and Sticker properties

	@property
	def private_channels(self) -> Sequence[PrivateChannel]:
		return utils.SequenceProxy(self._private_channels.values())

	def _get_private_channel(self, channel_id: Optional[str]) -> Optional[PrivateChannel]:
		try:
			value = self._private_channels[channel_id]
		except KeyError:
			return None
		else:
			self._private_channels.move_to_end(channel_id)
			return value

	def _get_private_channel_by_user(self, user_id: Optional[str]) -> Optional[DMChannel]:
		return self._private_channel_by_user.get(user_id)
	
	def _add_private_channel(self, channel: PrivateChannel) -> None:
		channel_id = channel.id
		self._private_channels[channel_id] = channel

		if len(self._private_channels) > 128:
			_, to_remove = self._private_channels.popitem(last=False)
			if isinstance(to_remove, DMChannel) and to_remove.recipient:
				self._private_channel_by_user.pop(to_remove.recipient.id, None)

		if isinstance(channel, DMChannel) and channel.recipient:
			self._private_channel_by_user[channel.recipient.id] = channel

	def add_dm_channel(self, data: DMChannelPayload) -> DMChannel:
		channel = DMChannel(me=self.user, state=self, data=data)
		self._add_private_channel(channel)
		return channel

	
