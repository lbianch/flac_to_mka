def str_from_int(func):
    """Function to be used as a decorator for a member method which
    returns some type convertible to `int` and accepts no arguments.
    The return value will be converted first to an `int` then to a
    `str` and is expanded with leading zeros on the left to be at least
    2 digits.
    """
    def wrapped(self):
        return str(int(func(self))).zfill(2)
    return wrapped


class Time:
    """A class used to generate CUE and Matroska time codes.
    The constructor accepts a parameter, ``time`` which defaults
    to ``0.0`` and should be a real number.
    """
    def __init__(self, time=0.0):
        self.time = time

    @str_from_int
    def Hours(self):
        return self.time // 3600

    @str_from_int
    def Minutes(self):
        return (self.time % 3600) // 60

    @str_from_int
    def CueMinutes(self):
        return self.time // 60

    @str_from_int
    def Seconds(self):
        return self.time % 60

    @str_from_int
    def Frames(self):
        return 75.0 * (self.time % 1)

    def Fractional(self):
        # time%1 is something like 0.XXXX
        # so converting to str and taking [2:]
        # captures only the fractional XXXX part
        return str(self.time % 1)[2:11].ljust(9, '0')

    def CueCode(self):
        return "{}:{}:{}".format(self.CueMinutes(), self.Seconds(), self.Frames())

    def MKACode(self):
        return "{}:{}:{}.{}".format(self.Hours(), self.Minutes(), self.Seconds(), self.Fractional())

    def __iadd__(self, t):
        self.time += t.time if isinstance(t, Time) else t
        return self


def CueTimeToMKATime(cue_time):
    """Converts a time signature from MM:SS:FF to a Matroska time code.
    Expects the input parameter to be either a `str` with two colon characters
    or a type from which `Time` can be produced, ie, a `float`.
    """
    if isinstance(cue_time, str):
        cue_time = [float(x) for x in cue_time.split(":")]
        minutes, seconds, frames = cue_time
        cue_time = minutes * 60.0
        cue_time += seconds
        cue_time += frames / 75.0
    return Time(cue_time).MKACode()
