class Utils:

    def __init__(self, config):
        self.config = config

    def IfOwner(self, userid):
        for user in self.config.ADMINISTRATORS:
            if userid == user["userid"]:
                if user["type"] == 0:
                    return True
        return False

    def IfAdmin(self, userid):
        for user in self.config.ADMINISTRATORS:
            if userid == user["userid"]:
                if user["type"] <= 1:
                    return True
        return False
