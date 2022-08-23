from __future__ import annotations
from typing import Union, Sequence, TYPE_CHECKING, Any

__all__ = [
	'AllowedMentions'
]

if TYPE_CHECKING:
	from typing_extensions import Self

class _FakeBool:
	def __repr__(self) -> str:
		return 'True'

	def __eq__(self, other: Self) -> bool:
		return other is True

	def __bool__(self) -> bool:
		return True

default: Any = _FakeBool()

# TODO: Determine if this is needed for the Mattermost API
class AllowedMentions:
	"""A class that represents what mentions are allowed in a message"""

	__slots__ = ('everyone', 'users', 'roles', 'replied_user')

	def __init__(
		self,
		*,
		everyone: bool = default,
		users: Union[bool, Sequence[Snowflake]] = default,
		roles: Union[bool, Sequence[Snowflake]] = default,
		replied_user: bool = default
	) -> None:
		self.everyone: bool = everyone
		self.users: Union[bool, Sequence[Snowflake]] = users
		self.roles: Union[bool, Sequence[Snowflake]] = roles
		self.replied_user: bool = replied_user

	@classmethod
	def all(cls) -> Self:
		"""A factory method that returns AllowedMentions with all fields True"""
		return cls(everyone=True, users=True, roles=True, replied_user=True)

	@classmethod
	def none(cls) -> Self:
		"""A factory method that returns AllowedMentions with all fields False"""
		return cls(everyone=False, users=False, roles=False, replied_user=False)

	def to_dict(self) -> AllowedMentionsPayload:
		parse = []
		data = {}

		if self.everyone:
			parse.append('everyone')

		if self.users == True:
			parse.append('users')
		elif self.users != False:
			data['users'] = [u.id for u in self.users]

		if self.roles == True:
			parse.append('roles')
		elif self.roles != False:
			data['roles'] = [r.id for r in self.roles]

		if self.replied_user:
			data['replied_user'] = True

		data['parse'] = parse
		return data

	def merge(self, other: AllowedMentions) -> AllowedMentions:
		everyone = self.everyone if other.everyone is default else other.everyone
		users = self.users if other.users is default else other.users
		roles = self.roles if other.roles is default else other.roles
		replied_user = self.replied_user if other.replied_user is default else other.replied_user
		return AllowedMentions(everyone=everyone, users=users, roles=roles, replied_user=replied_user)

	def __repr__(self) -> str:
		return (
			f'{self.__class__.__name__}(everyone={self.everyone}, '
			f'users={self.users}, roles={self.roles}, replied_user={self.replied_user}'
		)