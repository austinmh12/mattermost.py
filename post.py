from __future__ import annotations

import asyncio
from datetime import datetime
import re
import io
from os import PathLike
from typing import (
	Callable,
	ClassVar,
	Dict,
	TYPE_CHECKING,
	Sequence,
	Type,
	Union,
	overload,
	Optional,
	Any,
	List,
	Tuple
)

# Local imports
from . import utils
from .errors import HTTPException
from .member import Member
from .file import File
from .utils import MISSING #, escape_mentions # TODO: Figure out mentions in mm
from .http import handle_post_parameters
from .team import Team
from .threads import Thread
from .channel import PartialPostable

if TYPE_CHECKING:
	from typing_extensions import Self

	from .abc import TeamChannel, PostableChannel
	from .state import ConnectionState
	from .channel import TextChannel
	from .user import User

__all__ = [
	# 'Attachment',
	'Post',
	'PartialPost',
	# 'PostInteraction',
	'PostReference',
	'DeletedReferencedPost',
	# 'PostApplication'
]

def convert_emoji_reaction(emoji) -> str:
	...

class Attachment(Hashable):
	"""Represents an attachment from Mattermost"""

	__slots__ = (
		'id',
		'user_id',
		'post_id',
		'create_at',
		'update_at',
		'delete_at',
		'name',
		'extension',
		'size',
		'mime_type',
		'width',
		'height',
		'has_preview_image',
		'_http'
	)

	def __init__(self, *, data: AttachmentPayload, state: ConnectionState) -> None:
		self.id: str = data['id']
		self.user_id: str = data['user_id']
		self.post_id: str = data['post_id']
		self.create_at: datetime = data['create_at']
		self.update_at: datetime = data['update_at']
		self.delete_at: datetime = data['delete_at']
		self.name: str = data['name']
		self.extension: str = data['extension']
		self.size: int = data['size']
		self.mime_type: str = data['mime_type']
		self.width: int = data['width']
		self.height: int = data['height']
		self.has_preview_image: bool = data['has_preview_image']
		self._http = state.http

	def is_spoiler(self) -> bool:
		...

	def __repr__(self) -> str:
		return f'<Attachment id={self.id} filename={self.name!r}.{self.extension}>'

	def __str__(self) -> str:
		return f'{self.name!r}.{self.extension}'

	async def save(
		self,
		fp: Union[io.BufferedIOBase, PathLike[Any]],
		*,
		seek_begin: bool = True,
		use_cached: bool = False
	) -> int:
		...

	async def read(self, *, use_cached: bool = False) -> bytes:
		...

	async def to_file(
		self,
		*,
		filename: Optional[str] = MISSING,
		use_cached: bool = False,
		spoiler: bool = False,
	) -> File:
		...

	def to_dict(self) -> AttachmentPayload:
		...

class DeletedReferencedPost:
	"""Special sentinel type given when the resovled post reference points to a deleted post."""

	__slots__ = ('_parent')

	def __init__(self, parent: PostReference) -> None:
		self._parent: PostReference = parent

	def __repr__(self) -> str:
		return f'<DeletedReferencedPost id={self.id} channel_id={self.channel_id} team_id={self.team_id}'

	@property
	def id(self) -> str:
		return self._parent.post_id

	@property
	def channel_id(self) -> str:
		return self._parent.channel_id

	@property
	def team_id(self) -> str:
		return self._parent.team_id

class PostReference:
	"""Represents a reference to a Post"""
	
	__slots__ = (
		'post_id',
		'channel_id',
		'team_id',
		'fail_if_not_exists',
		'resolved',
		'_state'
	)

	def __init__(self, *, post_id: str, channel_id: str, team_id: Optional[str] = None, fail_if_not_exists: bool = True) -> None:
		self._state: Optional[ConnectionState] = None
		self.resolved: Optional[Union[Post, DeletedReferencedPost]] = None
		self.post_id: str = post_id
		self.channel_id: str = channel_id
		self.team_id: Optional[str] = team_id
		self.fail_if_not_exists: bool = fail_if_not_exists

	@classmethod
	def with_state(cls, state: ConnectionState, data: PostReferencePayload) -> Self:
		self = cls.__new__(cls)
		self.post_id = data['post_id']
		self.channel_id = data['channel_id']
		self.team_id = data.get('team_id')
		self.fail_if_not_exists = data['fail_id_not_exists']
		self._state = state
		self.resolved = None
		return self

	@classmethod
	def from_post(cls, post: PartialPost, *, fail_if_not_exists: bool = True) -> Self:
		self = cls(
			post_id = post.id,
			channel_id = post.channel.id,
			team_id = getattr(post.team, 'id', None),
			fail_if_not_exists=fail_if_not_exists
		)
		self._state = post._state
		return self

	@property
	def cached_post(self) -> Optional[Post]:
		...

	def __repr__(self) -> str:
		return f'<Postreference post_id={self.post_id} channel_id={self.channel_id} team_id={self.team_id!r}'

	def to_dict(self) -> PostReferencePayload:
		...

class PostInteraction:
	...

class PostApplication:
	...

class PartialPost(Hashable):
	"""Represents a partial post to aid with working posts when only a post and channel ID are present"""

	__slots__ = ('channel', 'id', '_cs_team', '_state', 'team')

	def __init__(self, *, channel: PostableChannel, id: str) -> None:
		self.channel: PostableChannel = channel
		self._state: ConnectionState = channel._state
		self.id: str = id
		self.team: Optional[Team] = getattr(channel, 'team', None)

	def _update(self, data: PostUpdateEvent) -> None:
		# Needed for duck typing
		pass

	# Needed for duck typing
	pinned: Any = property(None, lambda x, y: None)

	# created_time
	# jump_url

	async def fetch(self) -> Post:
		...

	async def delete(self, *, delay: Optional[float] = None) -> None:
		...

	async def edit(
		self,
		*,
		message: Optional[str] = ...,
		attachments: Sequence[Union[Attachment, File]] = ...,
		delete_after: Optional[float] = ...,
	) -> Post:
		...

	async def publish(self) -> None:
		...

	async def pin(self, *, reason: Optional[str] = None) -> None:
		...

	async def unpin(self, *, reason: Optional[str] = None) -> None:
		...
	
	async def add_reaction(self, emoji, /) -> None:
		...

	async def remove_reaction(self, emoji, member) -> None:
		...

	async def clear_reaction(self, emoji) -> None:
		...

	async def clear_reactions(self) -> None:
		...

	async def create_thread(
		self,
		*,
		name: str
	) -> Thread:
		...

	async def reply(self, message: Optional[str] = None, **kwargs: Any) -> Post:
		...

	def to_reference(self, *, fail_if_not_exists: bool = True) -> PostReference:
		return PostReference.from_post(self, fail_if_not_exists=fail_if_not_exists)

	def to_post_reference_dict(self) -> PostReferencePayload:
		...

def flatten_handlers(cls: Type[Post]) -> Type[Post]:
	prefix = len('_handle_')
	handlers = [key[prefix:], value for key, value in cls.__dict__.items() if key.startswith('_handle_') and key != '_handle_member']
	handlers.append(('member', cls._handle_member))
	cls._HANDLERS = handlers
	return cls

@flatten_handlers
class Post(PartialPost, Hashable):
	"""Represents a post from Mattermost"""

	__slots__ = (
		'id',
		'create_at',
		'update_at',
		'delete_at',
		'edit_at',
		'author',
		'channel',
		'root',
		'original_id',
		'message',
		'type',
		'props',
		'hashtag',
		'file_ids',
		'pending_post_id',
		'embeds',
		'emojis',
		'files',
		'images',
		'reactions',
		'mention_everyone',
		'mentions',
		'pinned'
	)

	if TYPE_CHECKING:
		_HANDLERS: ClassVar[List[Tuple[str, Callable[..., None]]]]
		_CACHED_SLOTS: ClassVar[List[str]]
		# team: Optional[Team]
		reference: Optional[PostReference]
		mentions: List[Union[User, Member]]
		author: Union[User, Member]

	def __init__(
		self,
		*,
		state: ConnectionState,
		channel: PostableChannel,
		data: PostPayload
	) -> None:
		self.channel: PostableChannel = channel
		self.id: str = data['id']
		self._state: ConnectionState = state
		# self.reactions: List[Reaction] = [Reaction()]
		self.attachments: List[Attachment] = []
		# self.embeds: List[Embed] = []
		self.create_at: datetime = data['create_at']
		self.update_at: datetime = data['update_at']
		self.delete_at: datetime = data['delete_at']
		# self.root: Optional[Post] = data.get('root_id')
		self.props: Dict[str, Any] = data['props']
		self.hashtag: str = data['hashtag']
		self.message: str = data['message']

		try:
			self.team = channel.team
		except AttributeError:
			self.team = state._get_team(data['team_id'])

	def _add_reaction(self, data, emoji, user_id):
		...

	def _remove_reaction(self, data, emoji, user_id):
		...

	def _clear_emoji(self, emoji):
		...

	def _update(self, data) -> None:
		...

	def _handle_edited_timestamp(self, value) -> None:
		...

	def _handle_pinned(self, value: bool) -> None:
		self.pinned = value

	def _handle_mention_everyone(self, value: bool) -> None:
		self.mention_everyone = value

	def _handle_type(self, value) -> None:
		...

	def _handle_message(self, value: str) -> None:
		self.message = value

	def _handle_attachments(self, value) -> None:
		...

	def _handle_embeds(self, value) -> None:
		...

	def _handle_author(self, value) -> None:
		...

	def _handle_member(self, member) -> None:
		...

	def _handle_mentions(self, mentions) -> None:
		...

	def is_system(self) -> bool:
		...

	async def edit(
		self,
		*,
		message: Optional[str] = MISSING,
		delete_after: Optional[float] = None
	) -> Post:
		...

	async def add_files(self, *files: File) -> Post:
		...

	async def remove_attachments(self, *attachments: Attachment) -> Post:
		...