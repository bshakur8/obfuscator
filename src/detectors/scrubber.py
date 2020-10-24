from scrubadub import Scrubber


class ObfuscatorScrubber(Scrubber):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remove_all_detectors()

    def remove_all_detectors(self):
        self._detectors.clear()

    def iter_filth(self, text):
        """Iterate over the different types of filth that can exist."""
        # TODO: make more efficient
        return super().iter_filth(text)
