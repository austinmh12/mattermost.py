from __future__ import annotations

import asyncio
from collections import deque
import concurrent.futures
import logging
import struct
import sys
import time
import threading
import traceback
import zlib

from typing import (
	Any,
	Callable,
	Coroutine,
	TYPE_CHECKING,
	NamedTuple,
	Optional,
	Dict
)

import aiohttp

# local imports

_log = logging.getLogger(__name__)

__all__ = [
	'MattermostWebSocket',
	'KeepAliveHandler',
	'ReconnectWebSocket'
]

if TYPE_CHECKING:
	from typing_extensions import Self

	from .client import Client

class ReconnectedWebSocket(Exception):
	# Signals to safely reconnect the websocket.
	def __init__(self, *, resume: bool = True) -> None:
		self.resume: bool = resume
		self.op: str = 'RESUME' if resume else 'IDENTIFY'

class WebSocketClosure(Exception):
	# An exception to make up for aiohttp not sending a closure signal.
	pass

class EventListener(NamedTuple):
	predicate: Callable[[Dict[str, Any]], bool]
	event: str
	result: Optional[Callable[[Dict[str, Any]], Any]]
	future: asyncio.Future[Any]

class GatewayRateLimiter:
	def __init__(self) -> None:
		# This needs to pay attention to the last headers
		...

class KeepAliveHandler(threading.Thread):
	def __init__(
		self,
		*args: Any,
		ws: MattermostWebSocket,
		interval: Optional[float] = None,
		**kwargs: Any
	) -> None:
		super().__init__(*args, **kwargs)
		self.ws: MattermostWebSocket = ws
		self._main_thread_id: int = ws.thread_id
		self.interval: Optional[float] = interval
		self.daemon: bool = True
		self._stop_ev: threading.Event = threading.Event()
		self._last_ack: float = time.perf_counter()
		self._last_send: float = time.perf_counter()
		self._last_recv: float = time.perf_counter()
		self.latency: float = float('inf')
		self.heartbeat_timeout: float = ws._max_heartbeat_timeout

	def run(self) -> None:
		while not self._stop_ev.wait(self.interval):
			if self._last_recv + self.heartbeat_timeout < time.perf_counter():
				_log.warning('Stopped resonding to the gateway. Closing and restarting.')
				coro = self.ws.close(4000)
				f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)

				try:
					f.result()
				except Exception:
					_log.exception('An error occured while stopping the gateway. Ignoring')
				finally:
					self.stop()
					return

			data = self.get_payload()
			_log.debug(f'Keeping websocket alive')
			coro = self.ws.send_heartbeat(data)
			f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)
			try:
				# Block until sending is completed
				total = 0
				while True:
					try:
						f.result(10)
						break
					except concurrent.futures.TimeoutError:
						total += 10
						try:
							frame = sys._current_frames()[self._main_thread_id]
						except KeyError:
							msg = 'Blocking'
						else:
							stack = ''.join(traceback.format_stack(frame))
							msg = f'Blocking\nLoop thread traceback (most recent call last):\n{stack}'
						_log.warning(msg)

			except Exception:
				self.stop()
			else:
				self._last_send = time.perf_counter()

	def get_payload(self) -> Dict[str, Any]:
		# Need to actually learn what this is
		return {}

	def stop(self) -> None:
		self._stop_ev.set()

	def tick(self) -> None:
		self._last_recv = time.perf_counter()

	def ack(self) -> None:
		ack_time = time.perf_counter()
		self._last_ack = ack_time
		self.latency = ack_time - self._last_send
		if self.latency > 10:
			_log.warning(f'Websocket latency is {self.latency}ms')