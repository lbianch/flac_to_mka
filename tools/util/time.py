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
    The constructor accepts a parameter, ``time`` which
    defaults to ``0.0`` and should be a floating point
    number representing seconds.
    """
    def __init__(self, time=0.0):
        self.time = time

    @classmethod
    def FromCueCode(cls, time):
        """Helper method to create a `Time` object from a CUE time code
        Expected input is a `str` of the format 'MM:SS:FF'
        """
        minutes, seconds, frames = map(float, time.split(":"))
        return cls(60. * minutes + seconds + frames / 75.)

    @classmethod
    def FromMKATime(cls, time):
        """Helper method to create a `Time` object from a CUE time code.
        Expected input is a `str` of the format 'HH:MM:SS.ffff'
        """
        hours, minutes, seconds = map(float, time.split(":"))
        return cls(3600. * hours + 60. * minutes + seconds)

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
        return f"{self.CueMinutes()}:{self.Seconds()}:{self.Frames()}"

    def MKACode(self):
        return f"{self.Hours()}:{self.Minutes()}:{self.Seconds()}.{self.Fractional()}"

    def __iadd__(self, t):
        self.time += t.time if isinstance(t, Time) else t
        return self


def CueTimeToMKATime(cue_time):
    """Converts a time signature from MM:SS:FF to a Matroska time code.
    Expects the input parameter to be either a `str` with two colon characters
    or a type from which `Time` can be produced, ie, a `float`.
    """
    if isinstance(cue_time, float):
        return Time(cue_time).MKACode()
    return Time.FromCueCode(cue_time).MKACode()


def MKATimeToCueTime(mka_time):
    """Converts a time signature from 'HH:MM:SS.ffff' to a CUE time code.
    Expects the input parameter to be either a `str` with two colon
    characters and one period or a `float`.
    """
    if isinstance(mka_time, float):
        return Time(mka_time).CueCode()
    return Time.FromMKATime(mka_time).CueCode()
