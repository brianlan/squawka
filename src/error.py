class Error(Exception):
    pass


class EventGroupNameNotFound(Error):
    pass


class UnrecognizedURLFormat(Error):
    pass


class PageNumNotPresentInURL(Error):
    pass
