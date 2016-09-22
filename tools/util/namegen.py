from os import path
import logging

from tools.util import flacutil
logging = logging.getLogger(__name__)


class FileName:
    """A filename generation class.  Replaces the extension with another
    extension, unless the desired extension has been specifically overridden
    with dict-like bracket syntax.
    Usage:
        name = FileName('my_file.wav')
        print(name("mka")) # my_file.mka
        name["mka"] = 'my_special_output.mka'
        print(name("mka")) # my_special_output.mka
        print(name("flac")) # my_file.flac
    """

    def __init__(self, base):
        """Parameter ``base`` must be a path containing a '.', otherwise an
        exception is raised.
        """
        logging.debug('Base parameter is {}'.format(base))
        if base.rfind('.') < 0:
            raise ValueError("Expected path to file, received {}".format(base))
        self.basename = base[0:base.rfind('.')]
        self.reserved = {}
        
    def __call__(self, ext=""):
        if not ext:
            return self.basename
        if ext.replace(".", "") in self.reserved:
            return path.join(flacutil.DirectoryName(self.basename), self.reserved[ext.replace(".", "")])
        return self.EmbedName(ext)

    def EmbedName(self, ext=""):
        if not ext:
            return self.basename
        if ext[0] == '.':
            ext = ext[1:]
        return "{}.{}".format(self.basename, ext)

    def __setitem__(self, k, val):
        self.reserved[k.replace(".", "")] = val


def GetNamegen(param):
    if param is None:
        return None
    if isinstance(param, FileName):
        return param
    if isinstance(param, str):
        return FileName(param)
    raise TypeError("Valid inputs are ``namegen.FileName`` and ``str``, received {}".format(type(param)))
