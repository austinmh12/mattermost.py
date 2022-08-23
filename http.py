from __future__ import annotations

import asyncio
import logging
import sys
from typing import (
	TYPE_CHECKING,
	Any,
	ClassVar,
	Coroutine,
	Dict,
	Iterable,
	List,
	NamedTuple,
	Optional,
	Sequence,
	Type,
	TypeVar,
	Union,
)
from urllib.parse import quote as _uriquote
from collections import deque
import datetime

import aiohttp

# Local imports
from .errors import HTTPException, RateLimited, Forbidden, NotFound, LoginFailure, MattermostServerError, GatewayNotFound
from .file import File
from .gateway import MattermostClientWebSocketResponse
from .mentions import AllowedMentions
from . import __version__, utils
from .utils import MISSING

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
	from typing_extensions import Self

	from types import TracebackType

	T = TypeVar('T')
	BE = TypeVar('BE', bound=BaseException)
	Response = Coroutine[Any, Any, T]

async def json_or_text(response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
	text = await response.text(encoding='utf-8')
	try:
		if response.headers['content-type'] == 'application/json':
			return utils._from_json(text)
	except KeyError as e:
		_log.exception(e)
		pass
	return text

class MultipartParameters(NamedTuple):
	payload: Optional[Dict[str, Any]]
	multipart: Optional[List[Dict[str, Any]]]
	files: Optional[Sequence[File]]

	def __enter__(self) -> Self:
		return self

	def __exit__(
		self,
		exc_type: Optional[Type[BE]],
		exc: Optional[BE],
		traceback: Optional[TracebackType]
	) -> None:
		if self.files:
			for file in self.files:
				file.close()

def handle_message_parameters(
	content: Optional[str] = MISSING,
	*,
	username: str = MISSING,
	avatar_url: Any = MISSING,
	tts: bool = False,
	nonce: Optional[Union[int, str]] = None,
	flags: MessageFlags = MISSING,
	file: File = MISSING,
	files: Sequence[File] = MISSING,
	# embed: Optional[Embed] = MISSING,
	# embeds: Sequence[Embed] = MISSING,
	# attachments: Sequence[Union[Attachment, File]] = MISSING,
	# view: Optional[View] = MISSING,
	# allowed_mentions: Optional[AllowedMentions] = MISSING,
	message_reference: Optional[message.MessageReference], # All message related things will be posts instead
	# stickers: Optional[SnowflakeList] = MISSING, # Need to figure out what Snowflake list is, and I don't think mm does stickers
	# previous_allowed_mentions: Optional[AllowedMentions] = None,
	mention_author: Optional[bool] = None,
	thread_name: str = MISSING,
	channel_payload: Dict[str, Any] = MISSING
) -> MultipartParameters:
	# TODO: Need to look at the payloads for mm api to determine anything that can be removed/changed/added
	if files is not MISSING and file is not MISSING:
		raise TypeError('Cannot mix file and files keywords.')
	# if embeds is not MISSING and embed is not MISSING:
	# 	raise TypeError('Cannot mix embed and embeds keywords.')
	
	if file is not MISSING:
		files = [file]
	
	if attachments is not MISSING and files is not MISSING:
		raise TypeError('Cannot mix attachments and files keywords.')
	
	payload = {}
	# if embeds is not MISSING:
	# 	# Handle embeds. This may not be a thing in mm.
	# 	...
	# if embed is not MISSING:
	# 	# Handle embed, see above
	# 	...
	
	if content is not MISSING:
		if content is not None:
			payload['content'] = str(content)
		else:
			payload['content'] = None
	
	# if view is not MISSING:
	# 	if view is not None:
	# 		payload['components'] = view.to_components()
	# 	else:
	# 		payload['components'] = []
		
	if nonce is not None:
		payload['nonce'] = str(nonce)

	if message_reference is not MISSING:
		payload['message_reference'] = message_reference

	# if stickers is not MISSING:
	# 	# probably not needed
	# 	...

	payload['tts'] = tts
	if avatar_url:
		payload['avatar_url'] = str(avatar_url)
	
	if username:
		payload['username'] = username

	if flags is not MISSING:
		payload['flags'] = flags.value

	if thread_name is not MISSING:
		payload['thread_name'] = thread_name

	# if allowed_mentions:
	# 	if previous_allowed_mentions is not None:
	# 		payload['allowed_mentions'] = previous_allowed_mentions.merge(allowed_mentions).to_dict()
	# 	else:
	# 		payload['allowed_mentions'] = allowed_mentions.to_dict()
	# elif previous_allowed_mentions is not None:
	# 	payload['allowed_mentions'] = previous_allowed_mentions.to_dict()

	if mention_author is not None:
		if 'allowed_mentions' not in payload:
			payload['allowed_mentions'] = AllowedMentions().to_dict()
		payload['allowed_mentions']['replied_user'] = mention_author

	if attachments is MISSING:
		attachments = files
	else:
		files = [a for a in attachments if isinstance(a, File)]

	if attachments is not MISSING:
		file_index = 0
		attachments_payload = []
		for attachment in attachments:
			if isinstance(attachment, File):
				attachments_payload.append(attachment.to_dict(file_index))
				file_index += 1
			else:
				attachments_payload.append(attachment.to_dict())
		payload['attachments'] = attachments_payload

	# if channel_payload is not MISSING:
	# 	# TODO: Need to figure out what this is
	# 	...

	multipart = []
	if files:
		multipart.append({'name': 'payload_json', 'value': utils._to_json(payload)})
		payload = None
		for index, file in enumerate(files):
			multipart.append(
				{
					'name': f'files[{index}]',
					'value': file.fp,
					'filename': file.filename,
					'content_type': 'application/octet-stream'
				}
			)

	return MultipartParameters(payload=payload, multipart=multipart, files=files)

INTERNAL_API_VERSION: int = 4

def _set_api_version_url(url: str, value: int):
	global INTERNAL_API_VERSION

	if not isinstance(value, int):
		raise TypeError(f'Expected int, not {value.__class__!r}')

	if value not in (3, 4):
		# These are the only version I know of, but this will only support 4
		raise ValueError(f'Expected either 3 or 4, got {value}')

	INTERNAL_API_VERSION = value
	Route.BASE = f'{url}/api/v{value}'

class Route:
	BASE: ClassVar[str] = 'http://localhost/api/v4'

	def __init__(self, method: str, path: str, *, metadata: Optional[str] = None, **parameters: Any) -> None:
		self.path: str = path
		self.method: str = method
		self.metadata: Optional[str] = metadata
		url = self.BASE + self.path
		if parameters:
			url = url.format_map({k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})
		self.url: str = url

		# Major Params:
		self._parameters = parameters
		# self.channel_id: Optional[Snowflake] = parameters.get('channel_id') # I believe this can stay as channels
		# self.guild_id: Optional[Snowflake] = parameters.get('guild_id') # This may need to change to teams
		# self.webhook_id: Optional[Snowflake] = parameters.get('webhook_id')
		# self.webhook_token: Optional[str] = parameters.get('webhook_token')

	@property
	def key(self) -> str:
		"""The bucket key is used to represent the route in various mappings"""
		if self.metadata:
			return f'{self.method} {self.path}:{self.metadata}'
		return f'{self.method} {self.path}'

	@property
	def major_parameters(self) -> str:
		# return '+'.join(
		# 	str(k) for k in (self.channel_id, self.guild_id, self.webhook_id, self.webhook_token) if k is not None
		# )
		return str(self._parameters)

class Ratelimit:
	"""Represents a Mattermost rate limit"""

	__slots__ = (
		'limit',
		'remaining',
		'outgoing',
		'reset_after',
		'expires',
		'dirty',
		'_last_request',
		'_max_ratelimit_timeout',
		'_loop',
		'_pending_requests',
		'_sleeping'
	)

	def __init__(self, max_ratelimit_timeout: Optional[float]) -> None:
		self.limit: int = 1
		self.remaining: int = self.limit
		self.outgoing: int = 0
		self.reset_after: float = 0.0
		self.expires: Optional[float] = None
		self.dirty: bool = False
		self._max_ratelimit_timeout: Optional[float] = max_ratelimit_timeout
		self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
		self._pending_requests: deque[asyncio.Future[Any]] = deque()
		self._sleeping: asyncio.Lock = asyncio.Lock()
		self._last_request: float = self._loop.time()

	def __repr__(self) -> str:
		return (
			f'<RateLimitBucket limit={self.limit} remaining={self.remaining} pending_requests={len(self._pending_requests)}>'
		)

	def reset(self):
		self.remaining = self.limit - self.outgoing
		self.expires = None
		self.reset_after = 0.0
		self.dirty = False

	def update(self, response: aiohttp.ClientResponse, *, use_clock: bool = False) -> None:
		headers = response.headers
		self.limit = int(headers.get('X-Ratelimit-Limit', 1))

		if self.dirty:
			self.remaining = min(int(headers.get('X-Ratelimit-Remaining', 0)), self.limit - self.outgoing)
		else:
			self.remaining = int(headers.get('X-Ratelimie-Remaining', 0))
			self.dirty = True

		reset_after = headers.get('X-Ratelimit-Reset')
		if use_clock or not reset_after:
			utc = datetime.timezone.utc
			now = datetime.datetime.now(utc)
			reset = datetime.datetime.fromtimestamp(float(headers['X-Ratelimit-Reset']), utc)
			self.reset_after = (reset - now).total_seconds()
		else:
			self.reset_after = float(reset_after)

		self.expires = self._loop.time() + self.reset_after

	def _wake_next(self) -> None:
		while self._pending_requests:
			future = self._pending_requests.popleft()
			if not future.done():
				future.set_result(None)
				break

	def _wake(self, count: int = 1, *, exception: Optional[RateLimited] = None) -> None:
		awaken = 0
		while self._pending_requests:
			future = self._pending_requests.popleft()
			if not future.done():
				if exception:
					future.set_exception(exception)
				else:
					future.set_result(None)
				awaken += 1
			
			if awaken >= count:
				break

	async def _refresh(self) -> None:
		error = self._max_ratelimit_timeout and self.reset_after > self._max_ratelimit_timeout
		exception = RateLimited(self.reset_after) if error else None
		async with self._sleeping:
			if not error:
				await asyncio.sleep(self.reset_after)

		self.reset()
		self._wake(self.remaining, exception=exception)

	def is_expired(self) -> bool:
		return self.expires is not None and self._loop.time() > self.expires

	def is_inactive(self) -> bool:
		delta = self._loop.time() - self._last_request
		return delta >= 300 and self.outgoing == 0 and len(self._pending_requests) == 0

	async def acquire(self) -> None:
		self._last_request = self._loop.time()
		if self.is_expired():
			self.reset()

		if self._max_ratelimit_timeout is not None and self.expires is not None:
			# Check if we can pre-emptivelt block this request for having too large of a timeout
			current_reset_after = self.expires - self._loop.time()
			if current_reset_after > self._max_ratelimit_timeout:
				raise RateLimited(current_reset_after)

		while self.remaining <= 0:
			future = self._loop.create_future()
			self._pending_requests.append(future)
			try:
				await future
			except:
				future.cancel()
				if self.remaining > 0 and not future.cancelled():
					self._wake_next()
				raise

		self.remaining -= 1
		self.outgoing += 1

	async def __aenter__(self) -> Self:
		await self.acquire()
		return self

	async def __aexit__(self, type: Type[BE], value: BE, traceback: TracebackType) -> None:
		self.outgoing -= 1
		tokens = self.remaining - self.outgoing
		# Check whether the rate limit needs to be slept on
		# Note that this is a lock to prevent multiple rate limit objects from sleeping at once
		if not self._sleeping.locked():
			if tokens <= 0:
				await self._refresh()
			elif self._pending_requests:
				exception = (
					RateLimited(self.reset_after)
					if self._max_ratelimit_timeout and self.reset_after > self._max_ratelimit_timeout
					else None
				)
				self._wake(tokens, exception=exception)

class HTTPClient:
	"""Represents an HTTP client sending HTTP requests to the Mattermost API."""
	def __init__(
		self,
		loop: asyncio.AbstractEventLoop,
		connector: Optional[aiohttp.BaseConnector] = None,
		*,
		proxy: Optional[str] = None,
		proxy_auth: Optional[aiohttp.BasicAuth] = None,
		unsync_clock: bool = True,
		http_trace: Optional[aiohttp.TraceConfig] = None,
		max_ratelimit_timeout: Optional[float] = None
	) -> None:
		self.loop: asyncio.AbstractEventLoop = loop
		self.connector: aiohttp.BaseConnector = connector or MISSING
		self.__session: aiohttp.ClientSession = MISSING # filled with static_login
		# Route key -> Bucket hash
		self._bucket_hashes: Dict[str, str] = {}
		# Bucket Hash + Major Parameters -> Rate limit
		# or
		# Route key + Major Parameters -> Rate limit
		# When the key is the latter, it is used for temporary one shot requests
		# that don't have a bucket hash
		# When this reached 256 elements, it will try to evict based off of expiry
		self._buckets: Dict[str, Ratelimit] = {}
		self._global_over: asyncio.Event = MISSING
		self.token: Optional[str] = None
		self.proxy: Optional[str] = proxy
		self.proxy_auth: Optional[aiohttp.BasicAuth] = proxy_auth
		self.http_trace: Optional[aiohttp.TraceConfig] = http_trace
		self.use_clock: bool = not unsync_clock
		self.max_ratelimit_timeout: Optional[float] = max(30.0, max_ratelimit_timeout) if max_ratelimit_timeout else None
		self.user_agent: str = f'MattermostBot (https://github.com/austinmh12/mattermost.py {__version__}) Python/{sys.version_info[0]}.{sys.version_info[1]} aiohttp/{aiohttp.__version__}'

	def clear(self) -> None:
		if self.__session and self.__session.closed:
			self.__session = MISSING

	async def ws_connect(self, url: str, *, compress: int = 0) -> aiohttp.ClientWebSocketResponse:
		kwargs = {
			'proxy_auth': self.proxy_auth,
			'proxy': self.proxy,
			'max_msg_size': 0,
			'timeout': 30.0,
			'autoclose': False,
			'headers': {
				'User-Agent': self.user_agent
			},
			'compress': compress
		}

		return await self.__session.ws_connect(url, **kwargs)

	def _try_clear_expired_ratelimits(self) -> None:
		if len(self._buckets) < 256:
			return

		keys = [key for key, bucket in self._buckets.items() if bucket.is_inactive()]
		for key in keys:
			del self._buckets[key]

	def get_ratelimit(self, key: str) -> Ratelimit:
		try:
			value = self._buckets[key]
		except KeyError:
			self._buckets[key] = value = Ratelimit(self.max_ratelimit_timeout)
			self._try_clear_expired_ratelimits()
		return value

	async def request(
		self,
		route: Route,
		*,
		files: Optional[Sequence[File]] = None,
		form: Optional[Iterable[Dict[str, Any]]] = None,
		**kwargs: Any
	) -> Any:
		method = route.method
		url = route.url
		route_key = route.key
		bucket_hash = None
		try:
			bucket_hash = self._bucket_hashes[route_key]
		except KeyError:
			key = f'{route.key}:{route.major_parameters}'
		else:
			key = f'{bucket_hash}:{route.major_parameters}'
		
		ratelimit = self.get_ratelimit(key)

		# Header creation
		headers: Dict[str, str] = {
			'User-Agent': self.user_agent
		}

		if self.token is not None:
			headers['Authorization'] = f'Bearer {self.token}'
		# Checking if it's a JSON request
		if 'json' in kwargs:
			headers['Content-Type'] = 'application/json'
			kwargs['data'] = utils._to_json(kwargs.pop('json'))
		
		# Not sure what this is or if it's needed
		# try:
		# 	reason = kwargs.pop('reason')
		# except KeyError:
		# 	pass
		# else:
		# 	if reason:
		# 		headers['X-Audit-Log-Reason'] = _uriquote(reason, safe='/ ')

		kwargs['headers'] = headers

		# Proxy support
		if self.proxy is not None:
			kwargs['proxy'] = self.proxy
		if self.proxy_auth is not None:
			kwargs['proxy_auth'] = self.proxy_auth

		if not self._global_over.is_set():
			# Wait until the global lock is complete
			await self._global_over.wait()

		response: Optional[aiohttp.ClientResponse] = None
		data: Optional[Union[Dict[str, Any], str]] = None
		async with ratelimit:
			for tries in range(5):
				if files:
					for f in files:
						f.reset(seek=tries)

				if form:
					# With quote_fields=True '[' and ']' in file field names are escaped, which discord does not support
					# TODO: Need to see if this is an issue with Mattermost
					form_data = aiohttp.FormData(quote_fields=False)
					for params in form:
						form_data.add_field(**params)
					kwargs['data'] = form_data

				try:
					async with self.__session.request(method, url, **kwargs) as response:
						_log.debug(f'{method} {url} with {kwargs.get("data")} has returned {response.status}')

						# Errors have text involed so this is safe to call
						# TODO: Verify if this is the case with Mattermost
						data = await json_or_text(response)

						# Update and use the rate limit information from the response headers
						has_ratelimit_headers = 'X-Ratelimit-Remaining' in response.headers
						# TODO: I don't think the mm api utilizes the self._buckets or self._bucket_hash stuff,
						# it just sends Limit, Remaining, Reset. Could probably do away with the buckets?
						if has_ratelimit_headers:
							if response.status != 429:
								ratelimit.update(response, use_clock=self.use_clock)
								if ratelimit.remaining == 0:
									_log.debug(f'A rate limit bucket ({route_key}) has been exhausted. Pre-emptively rate limiting...')

						# Successful response, just return
						if 200 <= response.status < 300:
							_log.debug(f'{method} {url} has received {data}')
							return data

						# Being rate limited
						if response.status == 429:
							if isinstance(data, str):
								# Not an expected response from the API
								raise HTTPException(response, data)

							if ratelimit.remaining > 0:
								# This shouldn't occur as mm doesn't say anything about sub-rate limiting
								# but I'll put it here just in case
								_log.debug(f'{method} {url} received a 429 despite having {ratelimit.remaining} requests. This is a sub-ratelimit.')

							retry_after: float = data['retry_after']
							if self.max_ratelimit_timeout and retry_after > self.max_ratelimit_timeout:
								_log.warning(f'We are being reate limited. {method} {url} responded with 429. Timeout of {retry_after:.2f} was too long')
								raise RateLimited(retry_after)

							_log.warning(f'We are being reate limited. {method} {url} responded with 429. Retrying in {retry_after:.2f} seconds.')

							# check if it's a global ratelimit
							# TODO: I believe all rate-limits will be global, but I'll need to do more investigation
							is_global = data.get('global', False)
							if is_global:
								_log.warning(f'Global rate limit has been hit. Retrying in {retry_after:.2f} seconds.')
								self._global_over.clear()

							await asyncio.sleep(retry_after)
							_log.debug('Done sleeping for rate limit. Retrying...')

							# Release the global lock now that the global ratelimit has passed
							if is_global:
								self._global_over.set()
								_log.debug('Global rate limit is now over.')

							continue

						if response.status in (500, 502, 504, 524): # unconditional retry
							await asyncio.sleep(1 + tries * 2)
							continue

						# Usual errors
						if response.status == 403:
							raise Forbidden(response, data)
						elif response.status == 404:
							raise NotFound(response, data)
						elif response >= 500:
							raise MattermostServerError(response, data)
						else:
							raise HTTPException(response, data)

				except OSError as e:
					# Connection reset by peer
					if tries < 4 and e.errno in (54, 10054):
						await asyncio.sleep(1 + tries * 2)
						continue
					raise

			if response is not None:
				# Out of retries, raise.
				if response.status >= 500:
					raise MattermostServerError(response, data)

				raise HTTPException(response, data)

			raise RuntimeError('Unreachable code in HTTP handling')

	async def get_from_cdn(self, url: str) -> bytes:
		async with self.__session.get(url) as resp:
			if resp.status == 200:
				return await resp.read()
			elif resp.status == 404:
				raise NotFound(resp, 'asset not found')
			elif resp.status == 403:
				raise Forbidden(resp, 'cannot retrieve asset')
			else:
				raise HTTPException(resp, 'failed to get asset')

		raise RuntimeError('Unreachable')

	# State management
	async def close(self) -> None:
		if self.__session:
			await self.__session.close()

	# Login management
	async def static_login(self, url: str, token: str) -> user.User:
		...

	def logout(self) -> Response[None]:
		...

	# After this goes all the endpoints but I won't do these until the underlying 
	# functionality of these are done (e.g. Channels, Teams, Users, etc...)