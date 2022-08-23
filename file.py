from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, Union

import os
import io

from .utils import MISSING

__all__ = [
	'File'
]

# TODO: Investigate spoilers in mm
# def _strip_spoiler(filename: str) -> Tuple[str, bool]:
	# ...

class File:
	__slots__ = (
		'fp',
		'_filename',
		'spoiler',
		'description',
		'_original_pos',
		'_owner',
		'_closer'
	)

	def __init__(
		self,
		fp: Union[str, bytes, os.PathLike[Any], io.BufferedIOBase],
		filename: Optional[str] = None,
		*,
		spoiler: bool = MISSING,
		description: Optional[str] = None
	) -> None:
		if isinstance(fp, io.IOBase):
			if not (fp.seekable() and fp.readable()):
				raise ValueError(f'File buffer {fp!r} must be seekable and readable')
			self.fp: io.BufferedIOBase = fp
			self._original_pos = fp.tell()
			self._owner = False
		else:
			self.fp = open(fp, 'rb')
			self._original_pos = 0
			self._owner = True

		# aiohttp onl uses read and close from IOBase.
		# This class should control the closing of files
		# so it needs to be stubbed so it doesn't close unless
		# the class tells it to
		self._closer = self.fp.close
		self.fp.close = lambda: None

		if filename is None:
			if isinstance(fp, str):
				_, filename = os.path.split(fp)
			else:
				filename = getattr(fp, 'name', 'untitled')

		# self._filename, filename_spoiler = _strip_spoiler(filename)
		# if spoiler is MISSING:
		# 	spoiler = filename_spoiler

		self.spoiler: bool = False # TODO: Unhardcode this as soon as you find out how spoilers are handled in mm api
		self.description: Optional[str] = description

	@property
	def filename(self) -> str:
		"""Determines the filename to display when uploading"""
		return f'SPOILER_{self._filename}' if self.spoiler else self._filename

	@filename.setter
	def filename(self, value: str) -> None:
		# self._filename, self.spoiler = _strip_spoiler(value)
		self._filename, self.spoiler = (value, False) # TODO: Unhardcode this as soon as you find out how spoilers are handled in mm api

	def reset(self, *, seek: Union[int, bool] = True) -> None:
		# The seek param is needed because the retry-loop is iterated over
		# multiple times starting from 0, as an implementation quirk the resetting must
		# be done at the beginning before a request is done, since the first index is 0,
		# and thus false, then this prevents an unnecessary seek since it's the first request done.
		if seek:
			self.fp.seek(self._original_pos)

	def close(self) -> None:
		self.fp.close = self._closer
		if self._owner:
			self._closer()

	def to_dict(self, index: int) -> Dict[str, Any]:
		payload = {
			'id': index,
			'filename': self.filename
		}

		if self.description is not None:
			payload['description'] = self.description

		return payload