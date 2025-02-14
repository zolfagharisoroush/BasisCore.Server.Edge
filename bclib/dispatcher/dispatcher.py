"""Base class for dispaching request"""
import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Any
from functools import wraps

from bclib.cache import create_chaching
from bclib.listener import RabbitBusListener, MessageType
from bclib.predicate import Predicate, InList, Equal, Url, Between, NotEqual, GreaterThan, LessThan, LessThanEqual, GreaterThanEqual, Match, HasValue, Callback
from bclib.context import ClientSourceContext, ClientSourceMemberContext, WebContext, Context, RESTfulContext, RabbitContext, SocketContext, ServerSourceContext, ServerSourceMemberContext
from bclib.db_manager import DbManager
from bclib.utility import DictEx
from ..dispatcher.callback_info import CallbackInfo
from bclib.exception import HandlerNotFoundErr


class Dispatcher(ABC):
    """Base class for dispaching request"""

    def __init__(self, options: dict = None):
        self.options = DictEx(options)
        self.__look_up: 'dict[str, list[CallbackInfo]]' = dict()
        cache_options = self.options.cache if "cache" in self.options else None
        self.cache_manager = create_chaching(cache_options)
        self.db_manager = DbManager(self.options)
        self.__rabbit_dispatcher: 'list[RabbitBusListener]' = list()
        if "router" in self.options and "rabbit" in self.options.router:
            for setting in self.options.router.rabbit:
                self.__rabbit_dispatcher.append(
                    RabbitBusListener(setting, self))

    def socket_action(self, * predicates: (Predicate)):
        """Decorator for determine Socket action"""

        def _decorator(socket_action_handler: 'Callable[[SocketContext],None]'):
            @wraps(socket_action_handler)
            def wrapper(context: SocketContext):
                socket_action_handler(context)
                return True
            self._get_context_lookup(SocketContext.__name__)\
                .append(CallbackInfo([*predicates], wrapper))
            return socket_action_handler
        return _decorator

    def restful_action(self, * predicates: (Predicate)):
        """Decorator for determine RESTful action"""

        def _decorator(restful_action_handler: 'Callable[[RESTfulContext], dict]'):
            @wraps(restful_action_handler)
            def wrapper(context: RESTfulContext):
                return context.generate_responce(restful_action_handler(context))
            self._get_context_lookup(RESTfulContext.__name__)\
                .append(CallbackInfo([*predicates], wrapper))
            return restful_action_handler
        return _decorator

    def web_action(self, * predicates: (Predicate)):
        """Decorator for determine legacy web request action"""

        def _decorator(web_action_handler: 'Callable[[WebContext], str]'):
            @wraps(web_action_handler)
            def wrapper(context: WebContext):
                return context.generate_responce(web_action_handler(context))
            self._get_context_lookup(WebContext.__name__)\
                .append(CallbackInfo([*predicates], wrapper))
            return web_action_handler
        return _decorator

    def client_source_action(self, *predicates: (Predicate)):
        """Decorator for determine source action"""

        def _decorator(client_source_action_handler: 'Callable[[ClientSourceContext], Any]'):
            @wraps(client_source_action_handler)
            def wrapper(context: ClientSourceContext):
                data = client_source_action_handler(context)
                result_set = list()
                if data is not None:
                    for member in context.command.member:
                        member_context = ClientSourceMemberContext(
                            context, data, member)
                        dispath_result = self.dispatch(member_context)
                        result = {
                            "options": {
                                "tableName": member_context.table_name,
                                "keyFieldName": member_context.key_field_name,
                                "statusFieldName": member_context.status_field_name,
                                "mergeType": member_context.merge_type.value
                            },
                            "data": dispath_result
                        }
                        result_set.append(result)
                ret_val = {
                    "setting": {
                        "keepalive": False,
                    },
                    "sources": result_set
                }
                return context.generate_responce(ret_val)
            self._get_context_lookup(ClientSourceContext.__name__)\
                .append(CallbackInfo([*predicates], wrapper))
            return client_source_action_handler
        return _decorator

    def client_source_member_action(self, *predicates: (Predicate)):
        """Decorator for determine source member action methode"""

        def _decorator(client_source_member_handler: 'Callable[[ClientSourceMemberContext], Any]'):
            self._get_context_lookup(ClientSourceMemberContext.__name__)\
                .append(CallbackInfo([*predicates], client_source_member_handler))
            return client_source_member_handler
        return _decorator

    def server_source_action(self, *predicates: (Predicate)):
        """Decorator for determine source action"""

        def _decorator(server_source_action_handler: 'Callable[[ServerSourceContext], Any]'):
            @wraps(server_source_action_handler)
            def wrapper(context: ServerSourceContext):
                data = server_source_action_handler(context)
                result_set = list()
                if data is not None:
                    for member in context.command.member:
                        member_context = ServerSourceMemberContext(
                            context, data, member)
                        dispath_result = self.dispatch(member_context)
                        result = {
                            "options": {
                                "tableName": member_context.table_name,
                                "keyFieldName": member_context.key_field_name,
                                "statusFieldName": member_context.status_field_name,
                                "mergeType": member_context.merge_type.value
                            },
                            "data": dispath_result
                        }
                        result_set.append(result)
                ret_val = {
                    "setting": {
                        "keepalive": False,
                    },
                    "sources": result_set
                }
                return context.generate_responce(ret_val)
            self._get_context_lookup(ServerSourceContext.__name__)\
                .append(CallbackInfo([*predicates], wrapper))
            return server_source_action_handler
        return _decorator

    def server_source_member_action(self, *predicates: (Predicate)):
        """Decorator for determine server source member action methode"""

        def _decorator(server_source_member_action_handler: 'Callable[[ServerSourceMemberContext], Any]'):
            self._get_context_lookup(ServerSourceMemberContext.__name__)\
                .append(CallbackInfo([*predicates], server_source_member_action_handler))
            return server_source_member_action_handler
        return _decorator

    def rabbit_action(self, * predicates: (Predicate)):
        """Decorator for determine rabbit-mq message request action"""

        def _decorator(rabbit_action_handler: 'Callable[[RabbitContext], None]'):
            @wraps(rabbit_action_handler)
            def wrapper(context: RabbitContext):
                rabbit_action_handler(context)
                return True
            self._get_context_lookup(RabbitContext.__name__)\
                .append(CallbackInfo([*predicates], wrapper))
            return wrapper
        return _decorator

    def _get_context_lookup(self, key: str) -> 'list[CallbackInfo]':
        """Get key related action list object"""

        ret_val: None
        if key in self.__look_up:
            ret_val = self.__look_up[key]
        else:
            ret_val = list()
            self.__look_up[key] = ret_val
        return ret_val

    def dispatch(self, context: Context) -> Any:
        """Dispatch context and get result from related action methode"""

        result: Any = None
        name = type(context).__name__
        try:
            items = self._get_context_lookup(name)
            for item in items:
                result = item.try_execute(context)
                if result is not None:
                    break
            else:
                result = context.generate_error_responce(
                    HandlerNotFoundErr(name))
        except Exception as ex:
            result = context.generate_error_responce(ex)
        return result

    def listening(self):
        for dispacher in self.__rabbit_dispatcher:
            dispacher.start_listening()

    def run_in_background(self, callback: Callable, *args: Any) -> Any:
        """helper for run function in background thread"""

        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, callback, *args)

    @abstractmethod
    def send_message(self, message: MessageType) -> bool:
        """Send message to endpoint"""

    def cache(self, seconds: int = 0, key: str = None):
        """Cache result of function for seconds of time or until signal by key for clear"""

        return self.cache_manager.cache_decorator(seconds, key)

    @staticmethod
    def in_list(expression: str, *items) -> Predicate:
        """Create list cheking predicate"""

        return InList(expression,  *items)

    @staticmethod
    def equal(expression: str, value: Any) -> Predicate:
        """Create equality cheking predicate"""

        return Equal(expression, value)

    @staticmethod
    def url(pattern: str) -> Predicate:
        """Create url cheking predicate"""

        return Url(pattern)

    @staticmethod
    def between(expression: str, min_value: int, max_value: int) -> Predicate:
        """Create between cheking predicate"""

        return Between(expression, min_value, max_value)

    @staticmethod
    def not_equal(expression: str, value: Any) -> Predicate:
        """Create not equality cheking predicate"""

        return NotEqual(expression, value)

    @staticmethod
    def greater_than(expression: str, value: int) -> Predicate:
        """Create not greater than cheking predicate"""

        return GreaterThan(expression, value)

    @staticmethod
    def less_than(expression: str, value: int) -> Predicate:
        """Create not less than cheking predicate"""

        return LessThan(expression, value)

    @staticmethod
    def less_than_equal(expression: str, value: int) -> Predicate:
        """Create not less than and equal cheking predicate"""

        return LessThanEqual(expression, value)

    @staticmethod
    def greater_than_equal(expression: str, value: int) -> Predicate:
        """Create not less than and equal cheking predicate"""

        return GreaterThanEqual(expression, value)

    @staticmethod
    def match(expression: str, value: str) -> Predicate:
        """Create regex matching cheking predicate"""

        return Match(expression, value)

    @staticmethod
    def has_value(expression: str) -> Predicate:
        """Create has value cheking predicate"""

        return HasValue(expression)

    @staticmethod
    def callback(callback: 'Callable[[Context],bool]') -> Predicate:
        """Create Callback cheking predicate"""

        return Callback(callback)
