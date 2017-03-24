import mutagen.flac


class FLACVerifier:
    """Class designed to ensure that a collection of FLAC filenames
    correspond to the same audio format (frequency, bit-depth, and channels).
    Additionally detects CD vs non-CD specification.  Typical usage:
      files = ['test.flac', 'test2.flac'] # Any iterable collection of ``str``
      FLACVerifier(files) # raises ``RuntimeError`` if files are not uniform
    Supported bit-depths: 16, 24
    Supported channels: 1, 2, 6
    Supported frequency (Hz): 44100, 48000, 88200, 96000, 176400, 192000
    """

    def __init__(self, files=None):
        self.ExpectedFreq = None
        self.ExpectedBits = None
        self.ExpectedChan = None
        if isinstance(files, str) and files:
            files = [files]
        if files:
            self.VerifyFiles(files)

    def __bool__(self):
        # These variables can't be zero, but they are initialized to None
        fields = [self.ExpectedChan, self.ExpectedBits, self.ExpectedFreq]
        return all(x is not None for x in fields)

    def _load_file(self, info):
        # Expect to find a file with sample frequency 44.1, 48, 88.2, 96, 176.4 or 192 kHz
        # With either 1, 2, or 6 channels
        # And a bit depth of either 16 or 24 bits
        info = mutagen.flac.FLAC(info).info
        if info.sample_rate not in [44100, 48000, 88200, 96000, 176400, 192000]:
            raise RuntimeError(f"Invalid sample rate in {info} of {info.sample_rate}")
        if info.channels not in [1, 2, 6]:
            raise RuntimeError(f"Invalid channels in {info} of {info.channels}")
        if info.bits_per_sample not in [16, 24]:
            raise RuntimeError(f"Invalid bitdepth in {info} of {info.bits_per_sample}")
        self.ExpectedFreq = info.sample_rate
        self.ExpectedChan = info.channels
        self.ExpectedBits = info.bits_per_sample

    def _verify_file(self, filename, info):
        if not self:
            raise RuntimeError("Must call _load_file before _verify_file")
        if info.sample_rate != self.ExpectedFreq:
            err = f"Mismatched sample rate in {filename}, expected {self.ExpectedFreq} received {info.sample_rate}"
            raise RuntimeError(err)
        if info.channels != self.ExpectedChan:
            err = f"Mismatched channels in {filename}, expected {self.ExpectedChan} received {info.channels}"
            raise RuntimeError(err)
        if info.bits_per_sample != self.ExpectedBits:
            err = f"Mismatched bit depth in {filename}, expected {self.ExpectedBits} received {info.bits_per_sample}"
            raise RuntimeError(err)

    def _KHz(self):
        if not self:
            return "Unknown"
        khz = str(self.ExpectedFreq/1000)
        return khz.replace(".0", "")

    def _Channels(self):
        # Limited to 1, 2, 6 and 2 is most likely
        return {2: "2.0", 6: "5.1", 1: "1.0"}[self.ExpectedChan]
        
    def __str__(self):
        if not self:
            return "FLACVerifier()"
        return f"FLACVerifier<{self._KHz()}kHz {self._Channels()} {self.ExpectedBits}-bit FLAC>"

    def IsCD(self):
        return self.ExpectedFreq == 44100 and self.ExpectedChan == 2 and self.ExpectedBits == 16
        
    def VerifyFile(self, f):
        info = mutagen.flac.FLAC(f).info
        self._verify_file(f, info)

    def VerifyFiles(self, files):
        self._load_file(files[0])
        for f in files[1:]:
            self.VerifyFile(f)
