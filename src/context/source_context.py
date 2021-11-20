import json
from typing import Any
from utility import BasisCoreHtmlParser
from utility.DictEx import DictEx
from .request_context import RequestContext


class SourceContext(RequestContext):
    """Context for dbSource request"""

    def __init__(self, request, options: dict) -> None:
        super().__init__(request, options)
        parser = BasisCoreHtmlParser()
        html = self.request.form.command
        parser.feed(html)
        self.__command = parser.get_dict_ex()
        self.process_async = True

    @property
    def command(self) -> DictEx:
        return self.__command

    def generate_responce(self, result: Any) -> dict:
        ret_val = super().generate_responce(result)
        ret_val["cms"]["content"] = json.dumps(result)
        ret_val["cms"]["webserver"] = {
            "index": "5",
            "headercode": "200 Ok",
            "mime": "application/json"
        }
        return ret_val
