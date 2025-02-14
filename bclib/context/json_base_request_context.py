import json
from typing import TYPE_CHECKING

from bclib.utility import HttpMimeTypes
from bclib.listener.http_listener import HttpBaseDataName, HttpBaseDataType
from ..context.request_context import RequestContext

if TYPE_CHECKING:
    from .. import dispatcher


class JsonBaseRequestContext(RequestContext):
    """Base class for dispatching http json base request context"""

    def __init__(self, cms_object: dict,  dispatcher: 'dispatcher.IDispatcher') -> None:
        super().__init__(cms_object, dispatcher)
        self.mime = HttpMimeTypes.JSON

    def generate_error_responce(self,  exception: Exception) -> dict:
        """Generate error responce from process result"""
        error_object = self._generate_error_object(exception)
        return self.generate_responce(error_object)

    def generate_responce(self, result: dict) -> dict:
        """Generate responce from process result"""

        ret_val = super().generate_responce(result)
        ret_val[HttpBaseDataType.CMS][HttpBaseDataName.CONTENT] = json.dumps(
            result)
        return ret_val
