from bclib.context import Context
from ..predicate.predicate import Predicate


class GreaterThanEqual (Predicate):
    """Create greater than equal cheking predicate"""

    def __init__(self, expression: str, value: int) -> None:
        super().__init__(expression)
        self.__value = value

    def check(self, context: Context) -> bool:
        try:
            value = eval(self.exprossion, {}, {"context": context})
            return self.__value <= value
        except:  # pylint: disable=bare-except
            return False
