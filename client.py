"""
Copyright info goes here
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import sys
import os
from typing import (
	TYPE_CHECKING,
	Any,
	Callable,
	Dict,
	List,
	Optional,
	Tuple
)

import aiohttp

# Local imports

if TYPE_CHECKING:
	...

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
		self.ws: Any = None # type: ignore
		self._listeners: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}
		# shard stuff, idk if needed here
		# self.shard_id: Optional[int] = options.get('shard_id')
		# self.shard_count: Optional[int] = options.get('shard_count')

		# proxy
		# proxy_auth
		# unsync_clock # idk what this is
		# http_trace
		# max_ratelimit_timeout
		# self.http: HTTPClient = HTTPClient()