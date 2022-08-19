"""
Copyright info goes here
"""

from __future__ import annotations

import asyncio
from cgitb import handler
import datetime
import logging
import sys
import os
from typing import (
	TYPE_CHECKING,
	Any,
	Callable,
	Coroutine,
	Dict,
	List,
	Optional,
	Sequence,
	Tuple,
	Type
)

import aiohttp

# Local imports

if TYPE_CHECKING:
	from typing_extensions import Self
	from types import TracebackType

__all__ = (
	'Client'
)

_log = logging.getLogger(__name__)

class _LoopSentinel:
	__slots__ = ()

	def __getattr__(self, attr: str) -> None:
		msg = (
			'loop attribute cannot be accessed in non-async contexts. '
			'Consider using either an asynchronous main function and passing it to asyncio.run or '
			'using asynchronous initialization hooks such as Client.setup_hook'
		)
		raise AttributeError(msg)

_loop: Any = _LoopSentinel()

class Client:
	"""Respresents a client connection to Mattermost"""
	def __init__(self, *, **options: Any) -> None:
		self.loop: asyncio.AbstractEventLoop = _loop
		# self.ws is set in the connect method
		self.ws: MattermostWebSocket = None # type: ignore
		self._listeners: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}
		# shard stuff, idk if needed here
		# self.shard_id: Optional[int] = options.get('shard_id')
		# self.shard_count: Optional[int] = options.get('shard_count')

		proxy = Optional[str] = options.pop('proxy', None)
		proxy_auth: Optional[aiohttp.BasicAuth] = options.pop('proxy_auth', None)
		unsync_clock: bool = options.pop('assume_unsync_clock', True) # idk what this is
		http_trace: Optional[aiohttp.TraceConfig] = options.pop('http_trace', None)
		max_ratelimit_timeout: Optional[float] = options.pop('max_ratelimit_timeout', None)
		self.http: HTTPClient = HTTPClient(
			self.loop,
			proxy=proxy,
			proxy_auth=proxy_auth,
			unsync_clock=unsync_clock,
			http_trace=http_trace,
			max_ratelimit_timeout=max_ratelimit_timeout
		)

		self._handlers: Dict[str, Callable[..., None]] = {
			'ready': self._handle_ready,
		}

		self._hooks: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {
			'before_identify': self._call_before_identify_hook,
		}

		self._enable_debug_events: bool = options.pop('enable_debug_events', False)
		self._connection: ConnectionState = self._get_state(**options) # I'm not sure I need intents
		# self._connection.shard_count = self.shard_count
		self._closed: bool = False
		self._ready: asyncio.Event: MISSING
		self._application: Optional[AppInfo] = None
		self._connection._get_websocket = self._get_websocket
		self._connection._get_client = lambda: self

		# Not doing voice support

	async def __aenter__(self) -> Self:
		await self._async_setup_hook()
		return self

	async def __aexit__(
		self,
		exc_type: Optional[Type[BaseException]],
		exc_value: Optional[BaseException],
		traceback: Optional[TracebackType]
	) -> None:
		if not self.is_closed():
			await self.close()

	# internals
	def _get_websocket(self, team_id: Optional[int] = None, *args) -> MattermostWebSocket:
		return self.ws

	def _get_state(self, **options: Any) -> ConnectionState:
		return ConnectionState(dispatch=self.dispatch, handlers=self._handlers, hooks=self._hooks, http=self.http, **options)

	def _handle_ready(self) -> None:
		self._ready.set()

	@property
	def latency(self) -> float:
		ws = self.ws
		return float('nan') if not ws else ws.latency

	def is_ws_ratelimited(self) -> bool:
		if self.ws:
			return self.ws.is_ratelimited()
		return False

	@property
	def user(self) -> Optional[ClientUser]:
		return self._connection.user

	@property
	def teams(self) -> Sequence[Team]:
		return self._connection.teams

	@property
	def emojis(self) -> Sequence[Emoji]:
		return self._connection.emojis

	@property
	def cached_messages(self) -> Sequence[Message]:
		...

	@property
	def private_channels(self) -> Sequence[PrivateChannel]:
		return self._connection.private_channels

	@property
	def application_id(self) -> Optional[int]:
		return self._connection.application_id

	@property
	def application_flags(self):
		...

	@property
	def application(self) -> Optional[AppInfo]:
		return self._application

	def is_ready(self) -> bool:
		return self._ready is not MISSING and self._ready.is_set()

	async def _run_event(
		self,
		coro: Callable[..., Coroutine[Any, Any, Any]],
		event_name: str,
		*args: Any,
		**kwargs: Any
	) -> None:
		try:
			await coro(*args, **kwargs)
		except asyncio.CancelledError:
			pass
		except Exception:
			try:
				await self.on_error(event_name, *args, *kwargs)
			except asyncio.CancelledError:
				pass

	def _schedule_event(
		self,
		coro: Callable[..., Coroutine[Any, Any, Any]],
		event_name: str,
		*args: Any,
		**kwargs: Any
	) -> asyncio.Task:
		wrapped = self._run_event(coro, event_name, *args, **kwargs)
		return self.loop.create_task(wrapped, name=f'mattermost.py: {event_name}')

	def dispatch(self, event: str, /, *args: Any, **kwargs: Any) -> None:
		_log.debug(f'Dispatching event {event}')
		method = f'on_{event}'
		listeners = self._listeners.get(event)
		if listeners:
			removed = []
			for i, (future, condition) in enumerate(listeners):
				if future.cancelled():
					removed.append(i)
					continue
					
				try:
					result = condition(*args)
				except Exception as exc:
					future.set_exception(exc)
					removed.append(i)
				else:
					if result:
						if len(args) == 0:
							future.set_result(None)
						elif len(args) == 1:
							future.set_result(args[0])
						else:
							future.set_result(args)
						removed.append(i)
			if len(removed) == len(listeners):
				self._listeners.pop(event)
			else:
				for idx in reversed(removed):
					del listeners[idx]

		try:
			coro = getattr(self, method)
		except AttributeError:
			pass
		else:
			self._schedule_event(coro, method, *args, **kwargs)

	async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
		_log.exception(f'Ignoring exception in {event_method}')

	async def _call_before_identity_hook(self, *, initial: bool = False) -> None:
		await self.before_identity_hook(initial=initial)

	async def before_identity_hook(self, *, initial: bool = False) -> None:
		if not initial:
			await asyncio.sleep(5.0)

	async def _async_setup_hook(self) -> None:
		# Called whenever the client needs to initialize asyncio objects with a running loop
		loop = asyncio.get_running_loop()
		self.loop = loop
		self.http.loop = loop
		self._connection.loop = loop

		self._ready = asyncio.Event()

	async def setup_hook(self) -> None:
		# A coroutine to be called to setup the bot, by default this is blank.
		pass

	async def login(self, url: str, token: str) -> None:
		# Logs in the client to the url with the specified credentials
		_log.info(f'Logging in to {url} using static token')

		if self.loop is _loop:
			await self._async_setup_hook()

		if not isinstance(url, str):
			raise TypeError(f'Expected url to be a str, received {url.__class__!r}')
		url = url.strip()

		if not isinstance(token, str):
			raise TypeError(f'Expected token to be a str, received {token.__class__!r}')
		token = token.strip()

		data = await self.http.static_login(url, token)
		self._connection.user = ClientUser(state=self._connection, data=data)
		self._application = await self.application_info()
		if self._connection.application_id is None:
			self._connection.application_id = self._application.id

		if not self._connection.application_flags:
			self._connection.application_flags = self._application.flags

		await self.setup_hook()

	async def connect(self, *, reconnect: bool = True) -> None:
		# Creates a websocket connection and lets it listen to messages from Mattermost
		# This is a loop that runs the entire event system and miscellaneius aspects
		# of the library. Control is not resumed until the WebSocket connection is terminated.
		backoff = ExponentialBackoff()
		ws_params = {
			'initial': True
		}
		...

	async def close(self) -> None:
		# Closes the connection to Mattermost
		if self._closed:
			return

		self._closed = True
		await self._connection.close()

		if self.ws is not None and self.ws.open:
			await self.ws.close(code=1000) # Figure out what this is

		await self.http.close()

		if self._ready is not MISSING:
			self._ready.clear()

		self.loop = MISSING

	def clear(self) -> None:
		# Clears the internal state of the bot
		self._closed = False
		self._ready.clear()
		self._connection.clear()
		self.http.clear()

	async def start(self, url: str, token: str, *, reconnect: bool = True) -> None:
		# Shorthand for login + connect
		await self.login(url, token)
		await self.connect(reconnect=reconnect)

	def run(
		self,
		url: str,
		token: str,
		*,
		reconnect: bool = True,
		log_handler: Optional[logging.Handler] = MISSING,
		log_formatter: logging.Formatter = MISSING,
		log_level: int = MISSING,
		root_logger: bool = False
	) -> None:
		# A blocking call that abstracts away the event loop initialization from you.
		async def runner():
			async with self:
				await self.start(url, token, reconnect=reconnect)
		
		if log_handler is not None:
			utils.setup_logging(
				handler=log_handler,
				formatter=log_formatter,
				level=log_level,
				root=root_logger
			)

		try:
			asyncio.run(runner())
		except KeyboardInterrupt:
			# Nothing to do here, asyncio.run handles loop cleanup
			return

	# Properties
	def is_closed(self) -> bool:
		return self._closed

	# Need to look at the "activities" served by mattermost
	# @property
	# def activity(self) -> Optional[Activity]:
	# 	return create_activity()
	
	@property
	def status(self) -> Status:
		if self._connection._status in set(state.value for state in Status):
			return Status(self._connection._status)
		return Status.online

	@status.setter
	def status(self, value: Status) -> None:
		if value is Status.offline:
			self._connection._status = 'invisible'
		elif isinstance(value, Status):
			self._connection._status = str(value)
		else:
			raise TypeError('status must derive from Status.')