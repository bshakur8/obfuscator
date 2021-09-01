from scrubadub import Scrubber


class ObfuscatorScrubber(Scrubber):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._detectors.clear()
