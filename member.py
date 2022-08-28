from __future__ import annotations

from datetime import datetime
import inspect
import itertools
from operator import attrgetter
from typing import Any, Awaitable, Callable, Collection, Dict, List, Optional, TYPE_CHECKING, Tuple, TypeVar, Union

# Local imports
import mattermost.abc
from . import utils
from .utils import MISSING
from .user import BaseUser, User, _UserTag
from .enums import Status, try_enum
from .errors import ClientException

__all__ = [
	'Member'
]

T = TypeVar('T', bound=type)

if TYPE_CHECKING:
	from typing_extensions import Self

	from .channel import DMChannel
	from .team import Team
	from .state import ConnectionState
	from .post import Post

class _ClientStatus:
	...

def flatten_user(cls: T) -> T:
	for attr, value in itertools.chain(BaseUser.__dict__.items(), User.__dict__.items()):
		...

@flatten_user
class Member(mattermost.abc.Postable, _UserTag):
	__slots__ = (
		'team',
		'user_id',
		'roles',
		'delete_at',
		'scheme_user',
		'scheme_admin',
		'explicit_roles',
		'_state'
	)

	if TYPE_CHECKING:
		name: str
		id: str
		bot: bool
		system: bool
		dm_channel: Optional[DMChannel]
		create_dm: Callable[[], Awaitable[DMChannel]]
		mutual_teams: List[Team]

	def __init__(self, *, data: MemberWithUserPayload, team: Team, state: ConnectionState) -> None:
		self._state: ConnectionState = state
		self.user_id: str = data['user_id']
		self._user: User = None
		self.team: Team = team
	
	def __str__(self) -> str:
		return str(self._user)

	def __repr__(self) -> str:
		return f'<Member id={self.user_id}'

	def __eq__(self, other: object) -> bool:
		return isinstance(other, _UserTag) and other.id == self.id

	def __ne__(self, other: object) -> bool:
		return not self.__eq__(other)

	def __hash__(self) -> int:
		return hash(self._user)

	@classmethod
	def _from_post(cls, *, post: Post, data: MemberPayload) -> Self:
		...

	def _update_from_message(self, data: MemberPayload) -> None:
		...

	async def _get_channel(self) -> DMChannel:
		...

	def _update(self, data) -> None:
		...

	def _presence_update(self, data, user):
		...

	@property
	def mention(self) -> str:
		...

	def mentioned_in(self, post: Post) -> bool:
		...

	async def edit(
		self,
		*,
		display: Optional[str] = MISSING
	) -> Optional[Member]:
		...