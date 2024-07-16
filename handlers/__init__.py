from abc import ABCMeta, abstractmethod

class Handler(metaclass=ABCMeta):
    def __init__(self, module):
        self.bot = module.bot
        self.logger = module.logger

    @abstractmethod
    def handle(self) -> None:
        pass