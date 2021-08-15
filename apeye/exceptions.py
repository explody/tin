class ApeyeError(Exception):
    """Generic Apeye exception"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ApeyeConfigNotFound(Exception):
    """Config file not found exception"""

    def __init__(self, filename, paths):
        self.value = "Not found: [" + filename + "] I looked here:" + " ".join(paths)

    def __str__(self):
        return self.value


class ApeyeObjectNotFound(ApeyeError):
    """Exception thrown for 404 errors"""

    def __init__(self, value):
        super().__init__(value)


class ApeyeInvalidArgs(Exception):
    def __init__(self, value):
        super().__init__(value)


class ApeyeModelError(ApeyeError):
    def __init__(self, value):
        super().__init__(value)
