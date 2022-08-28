from typing import Optional, TypedDict
from datetime import datetime

from .user import User

class DisplayName(TypedDict):
	display_name: str

class PartialMember(TypedDict):
	...

class Member(PartialMember, total=False):
	user_id: str
	roles: str
	delete_at: datetime
	schema_user: bool
	schema_admin: bool
	explicit_roles: str

class _OptionalMemberWithUser(PartialMember, total=False):
	...

class MemberWithUser(_OptionalMemberWithUser):
	user: User

class UserWithMember(User, total=False):
	member: _OptionalMemberWithUser