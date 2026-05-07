import sys
import subprocess
import pathlib
from scrapy import signals
from scrapy.exceptions import NotConfigured

_SOUNDS_DIR = pathlib.Path(__file__).parent / "sounds"
_DEFAULT_SUCCESS = str(_SOUNDS_DIR / "success.wav")
_DEFAULT_FAILURE = str(_SOUNDS_DIR / "failure.wav")


class BeepExtension:
    """Plays a sound when a spider finishes — different tones for success vs failure.

    Settings:
        BEEP_ENABLED (bool, default True): set False to disable entirely.
        BEEP_SUCCESS_SOUND: path to a WAV file (overrides bundled sound).
        BEEP_FAILURE_SOUND: path to a WAV file (overrides bundled sound).
    """

    def __init__(self, success_sound, failure_sound):
        self.success_sound = success_sound
        self.failure_sound = failure_sound

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("BEEP_ENABLED", True):
            raise NotConfigured("BEEP_ENABLED is False")

        success = crawler.settings.get("BEEP_SUCCESS_SOUND", _DEFAULT_SUCCESS)
        failure = crawler.settings.get("BEEP_FAILURE_SOUND", _DEFAULT_FAILURE)

        ext = cls(success_sound=success, failure_sound=failure)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_closed(self, spider, reason):
        stats = spider.crawler.stats.get_stats()
        items = stats.get("item_scraped_count", 0)
        errors = stats.get("log_count/ERROR", 0)

        is_success = reason == "finished" and items > 0 and errors == 0

        spider.logger.info(
            "BeepExtension: reason=%s items=%d errors=%d → %s",
            reason,
            items,
            errors,
            "SUCCESS" if is_success else "FAILURE",
        )

        self._play(self.success_sound if is_success else self.failure_sound)

    @staticmethod
    def _play(path):
        if not path:
            return
        if sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        elif sys.platform == "win32":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
        else:
            subprocess.run(["aplay", path], check=False)
