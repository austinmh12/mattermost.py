from typing import Optional, TypedDict

class PartialUser(TypedDict):
	id: str
	username: str

class User(PartialUser, total=False):
	bot: bool
	system: bool
	mfa_active: bool
	email_verified: bool
	locale: str