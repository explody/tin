class TinError(Exception):
    """Generic Tin exception"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TinConfigNotFound(Exception):
    """Config file not found exception"""

    def __init__(self, filename):
        self.value = "Config not found: {}".format(filename)

    def __str__(self):
        return self.value


class TinObjectNotFound(TinError):
    """Exception thrown for 404 errors"""

    def __init__(self, value):
        super().__init__(value)


class TinInvalidArgs(Exception):
    def __init__(self, value):
        super().__init__(value)


class TinModelError(TinError):
    def __init__(self, value):
        super().__init__(value)
