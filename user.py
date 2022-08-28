from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

# Local imports
import mattermost.abc
from .utils import MISSING

if TYPE_CHECKING:
	from typing_extensions import Self
	from datetime import datetime
	from .channel import DMChannel
	from .post import Post
	from .state import ConnectionState
	from .team import Team
	from .payloads.channel import DMChannel as DMChannelPayload
	from .payloads.user import PartialUser as PartialUserPayload, User as UserPayload

__all__ = [
	'User',
	'ClientUser'
]

class _UserTag:
	__slots__ = ()
	id: str

class BaseUser(_UserTag):
	__slots__ = (
		'name',
		'id',
		'bot',
		'system',
		'_state'
	)

	if TYPE_CHECKING:
		name: str
		id: str
		bot: bool
		system: bool
		_state: ConnectionState

	def __init__(self, *, state: ConnectionState, data: Union[UserPayload, PartialUserPayload]) -> None:
		self._state = state
		self._update(data)

	def __repr__(self) -> str:
		return f'<BaseUser id={self.id} name={self.name!r} bot={self.bot} system={self.system}>'

	def __str__(self) -> str:
		return self.name

	def __eq__(self, other: object) -> bool:
		return isinstance(other, _UserTag) and other.id == self.id

	def __ne__(self, other: object) -> bool:
		return not self.__eq__(other)

	def __hash__(self) -> int:
		# Not entirely sure a hash is necessary for this library
		return hash(self.id) # >> 22 but this is because Discord uses Twitter's Snowflake thing and mm doesn't

	def _update(self, data: Union[UserPayload, PartialUserPayload]) -> None:
		self.name = data['username']
		self.id = data['id']
		self.bot = data.get('bot', False)
		self.system = data.get('system', False)

	@classmethod
	def _copy(cls, user: Self) -> Self:
		self = cls.__new__(cls) # Bypasses __init__
		self.name = user.name
		self.id = user.id
		self.bot = user.bot
		self.system = user.system
		self._state = user._state

		return self

	def _to_minimal_user_json(self) -> Dict[str, Any]:
		return {
			'username': self.name,
			'id': self.id,
			'bot': self.bot
		}

	# Skip colour, avatar, and banner stuff for now

	@property
	def mention(self) -> str:
		return f'<@{self.id}>' # TODO: Look at how mentions work in mm

	@property
	def display_name(self) -> str:
		return self.name

	def mentioned_in(self, post: Post) -> bool:
		if post.mention_everyone:
			return True
		
		return any(user.id == self.id for user in post.mentions)

class ClientUser(BaseUser):
	"""Represents your Mattermost user."""
	__slots__ = ('locale', 'verified', 'mfa_active', '__weakref__')

	if TYPE_CHECKING:
		verified: bool
		locale: Optional[str]
		mfa_active: bool

	def __init__(self, *, state: ConnectionState, data: UserPayload) -> None:
		super().__init__(state=state, data=data)

	def __repr__(self) -> str:
		return f'<ClientUser id={self.id} name={self.name!r} bot={self.bot} verified={self.verified} mfa_active={self.mfa_active}>'

	def _update(self, data: UserPayload) -> None:
		super()._update(data)
		self.verified = data.get('email_verified', False)
		self.locale = data.get('locale')
		self.mfa_active = data.get('mfa_active', False)

	async def edit(self, *, username: str = MISSING) -> ClientUser:
		payload: Dict[str, Any] = {}
		if username is not MISSING:
			payload['username'] = username

		data: UserPayload = await self._state.http.edit_profile(payload)
		return ClientUser(state=self._state, data=data)

class User(BaseUser, mattermost.abc.Postable):
	__slots__ = ('__weakref__')

	def __repr__(self) -> str:
		return f'<User id={self.id} name={self.name!r} bot={self.bot}>'

	async def _get_channel(self) -> DMChannel:
		ch = await self.create_dm()
		return ch

	@property
	def dm_channel(self) -> Optional[DMChannel]:
		return self._state._get_private_channel_by_user(self.id)

	# Mutual teams

	async def create_dm(self) -> DMChannel:
		found = self.dm_channel
		if found is not None:
			return found

		state = self._state
		data: DMChannelPayload = await state.http.start_private_post(self.id)
		return state.add_dm_channel(data)
