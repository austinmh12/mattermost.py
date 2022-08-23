from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING, Any, Tuple, Union

if TYPE_CHECKING:
	from aiohttp import ClientResponse, ClientWebSocketResponse
	from requests import Response

	_ResponseType = Union[ClientResponse, Response]

__all__ = [
	'MattermostException',
	'ClientException',
	'GatewayNotFound',
	'HTTPException',
	'RateLimited',
	'Forbidden',
	'NotFound',
	'MattermostServerError',
	'InvalidData',
	'LoginFailure',
	'ConnectionClosed'
]

class MattermostException(Exception):
	"""Base exception class for mattermost.py"""
	pass

class ClientException(MattermostException):
	"""Exception raised when an operation in the client fails"""
	pass

class GatewayNotFound(MattermostException):
	def __init__(self) -> None:
		msg = 'A gateway to mattermost could not be found.'
		super().__init__(msg)

class HTTPException(MattermostException):
	"""Exception that is raised when an HTTP request fails"""
	def __init__(self, response: _ResponseType, message: Optional[Union[str, Dict[str, Any]]]) -> None:
		self.response: _ResponseType = response
		self.status: int = response.status
		self.code: int
		self.text: str
		if isinstance(message, dict):
			self.code = message.get('id', 0)
			self.text = message.get('message', '')

		else:
			self.text = message or ''
			self.code = 0

		super().__init__(f'{self.response.status} {self.response.reason} (error code: {self.code}){": " + self.text if self.text else ""}')

class RateLimited(MattermostException):
	"""Exception that's raised for 429 errors"""
	def __init__(self, retry_after: float) -> None:
		self.retry_after: float = retry_after
		super().__init__(f'Too many requests. Retry in {retry_after:.2f} seconds.')

class Forbidden(HTTPException):
	"""Exception that's raised on 403 errors"""
	pass

class NotFound(HTTPException):
	"""Exception that's raised on 404 errors"""
	pass

class MattermostServerError(HTTPException):
	"""Exception that's raised on 500+ errors"""
	pass

class InvalidData(ClientException):
	"""Exception that's raised when the library encounters an unknown error"""
	pass

class LoginFailure(ClientException):
	"""Exception that's raised when the client.login function fails to log you in
	from improper credentials or something else."""
	pass

class ConnectionClosed(ClientException):
	"""Exception that's raised when the gateway connection is closed for reasons
	that could not be handled internally"""
	def __init__(self, socket: ClientWebSocketResponse, *, code: Optional[int] = None):
		self.code: int = code or socket.close_code or -1
		self.reason: str = ''
		super().__init__(f'Websocket closed with {self.code}')