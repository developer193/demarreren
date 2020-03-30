class Error(Exception):
    """Base class for other exceptions"""
    pass

class NotEnoughCardsError(Error):
    pass

class WrongPlayerError(Error):
    pass
