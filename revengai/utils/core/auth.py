from abc import ABC, abstractmethod
from binaryninja import BinaryView

class BaseAuthFeature(ABC):
    def __init__(self, config=None):
        self.config = config
    
    @abstractmethod
    def register(self):
        pass

    def is_valid(self, bv: BinaryView):
        return self.config.is_configured == True 