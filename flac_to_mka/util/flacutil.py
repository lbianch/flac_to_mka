import os
import platform

from flac_to_mka.tools import config

if platform.system() == "Windows":
    import win32api
    import win32con

# Handle via config
configuration = config.GetConfig()
FLAC_EXE = configuration['flac']
METAFLAC_EXE = configuration['metaflac']
SOX_EXE = configuration['sox']
MKVMERGE_EXE = configuration['mkvmerge']
OUTPUTDIR = configuration['output']
del configuration


def DirectoryName(f):
    if os.path.isdir(f):
        return f
    dirname = os.path.dirname(f)
    if dirname and dirname != ".":
        return dirname
    return os.getcwd()


def FileName(f):
    if os.path.isdir(f):
        raise RuntimeError(f"Can't obtain filename from directory {f}")
    return os.path.basename(f)


def GetFilenames(exts, directory=".", case=False, abspath=True, exclude=()):
    """Returns a sorted ``list[str]`` containing the file names of all files in the
    directory ``directory`` with the extension(s) ``exts``.

    Parameters
    ----------
    exts: str or list[str], required
          Indicates the extension(s) that are desired
    directory: str, default='.'
          Location to search for files
    case: bool, default=False
          True to perform a case sensitive search, False for case insensitive
    abspath: bool, default=True
          True returns the ``directory`` and file names joined via os.path.join
          False returns just the file names
    exclude: list[str] or tuple(str), default=()
          A list of explicit file names to exclude -- note that if absolute paths
          are given then the directory is stripped off yielding just the file names.

    Returns
    -------
    list[str] containing the formatted file names, sorted
    """
    files = os.listdir(directory)
    if not isinstance(exts, list):
        exts = [exts]
    exclude = [FileName(f) for f in exclude]
    if case:
        files = [f for f in files if f not in exclude]
    else:
        exclude = [e.lower() for e in exclude]
        files = [f for f in files if not f.lower() in exclude]
    if case:  # Case SENSITIVE
        files = [f for f in files if any(f.endswith(ext) for ext in exts)]
    else:     # Case INSENSITIVE
        files = [f for f in files if any(f.lower().endswith(ext) for ext in exts)]
    if abspath:
        files = [os.path.join(directory, f) for f in files]
    files.sort()
    return files


def FileIsHidden(f):
    """Returns a boolean indicating whether the file ``f`` is hidden or not.
    This function is Windows/Linux safe.
    """
    if platform.system() == "Windows":
        # Note this is bitwise and as the RHS is a mask
        return bool(win32api.GetFileAttributes(f) & win32con.FILE_ATTRIBUTE_HIDDEN)
    # Linux/Mac hidden files simply have file names that start with a dot
    return FileName(f).startswith('.')
