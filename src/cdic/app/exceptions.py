# coding: utf-8
class PatchDockerfileException(Exception):
    pass


class FailedToFindProjectByDockerhubName(Exception):
    pass


class CoprSearchError(Exception):
    pass


class PopenError(Exception):
    def __init__(self, msg, return_code=None, stdout=None, stderr=None, **kwargs):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        super(PopenError, self).__init__(msg+self.msg_addition, **kwargs)

    @property
    def msg_addition(self):
        result = ""
        if self.return_code:
            result += "\nReturn code: {}".format(self.return_code)
        if self.stdout:
            result += "\nSTDOUT:\n{}".format(self.stdout)
        if self.stderr:
            result += "\nSTDERR:\n{}".format(self.stderr)
        return result


class DockerHubCreateRepoError(PopenError):
    pass


class DockerHubQueryError(PopenError):
    pass
