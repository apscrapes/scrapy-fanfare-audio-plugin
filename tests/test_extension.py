"""Unit tests for BeepExtension.

We mock subprocess.run and winsound so no actual audio plays during tests.
"""

import sys
from unittest.mock import MagicMock, patch, call

import pytest
from scrapy import Spider, signals
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.settings import Settings
from scrapy.statscollectors import MemoryStatsCollector

from scrapy_beep.addon import Addon
from scrapy_beep.extension import BeepExtension


def _make_crawler(extra_settings=None):
    settings_dict = {"BEEP_ENABLED": True}
    if extra_settings:
        settings_dict.update(extra_settings)
    settings = Settings(values=settings_dict)
    crawler = MagicMock()
    crawler.settings = settings
    crawler.signals = MagicMock()
    stats = MemoryStatsCollector(crawler)
    crawler.stats = stats
    return crawler


def _make_spider(crawler, items=0, errors=0):
    spider = MagicMock()
    spider.crawler = crawler
    crawler.stats.set_value("item_scraped_count", items)
    if errors:
        crawler.stats.set_value("log_count/ERROR", errors)
    return spider


class TestFromCrawler:
    def test_connects_spider_closed_signal(self):
        crawler = _make_crawler()
        BeepExtension.from_crawler(crawler)
        crawler.signals.connect.assert_called_once()
        _, kwargs = crawler.signals.connect.call_args
        assert kwargs["signal"] is signals.spider_closed

    def test_raises_not_configured_when_disabled(self):
        crawler = _make_crawler({"BEEP_ENABLED": False})
        with pytest.raises(NotConfigured):
            BeepExtension.from_crawler(crawler)


class TestSuccessDetection:
    def _closed(self, ext, spider, reason):
        ext.spider_closed(spider, reason)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_success_plays_success_sound(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=5, errors=0)

        ext.spider_closed(spider, reason="finished")

        mock_play.assert_called_once_with(ext.success_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_zero_items_plays_failure(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=0, errors=0)

        ext.spider_closed(spider, reason="finished")

        mock_play.assert_called_once_with(ext.failure_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_errors_play_failure(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=10, errors=2)

        ext.spider_closed(spider, reason="finished")

        mock_play.assert_called_once_with(ext.failure_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_itemcount_limit_plays_success(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=100, errors=0)

        ext.spider_closed(spider, reason="closespider_itemcount")

        mock_play.assert_called_once_with(ext.success_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_pagecount_limit_plays_success(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=50, errors=0)

        ext.spider_closed(spider, reason="closespider_pagecount")

        mock_play.assert_called_once_with(ext.success_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_timeout_limit_plays_success(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=20, errors=0)

        ext.spider_closed(spider, reason="closespider_timeout")

        mock_play.assert_called_once_with(ext.success_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_errorcount_limit_plays_failure(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=10, errors=0)

        ext.spider_closed(spider, reason="closespider_errorcount")

        mock_play.assert_called_once_with(ext.failure_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_shutdown_reason_plays_failure(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=10, errors=0)

        ext.spider_closed(spider, reason="shutdown")

        mock_play.assert_called_once_with(ext.failure_sound)

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_cancelled_reason_plays_failure(self, mock_play):
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=10, errors=0)

        ext.spider_closed(spider, reason="cancelled")

        mock_play.assert_called_once_with(ext.failure_sound)


class TestCustomSounds:
    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_custom_success_sound_used(self, mock_play):
        crawler = _make_crawler({"BEEP_SUCCESS_SOUND": "/tmp/custom_success.aiff"})
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=1)

        ext.spider_closed(spider, reason="finished")

        mock_play.assert_called_once_with("/tmp/custom_success.aiff")

    @patch("scrapy_beep.extension.BeepExtension._play")
    def test_custom_failure_sound_used(self, mock_play):
        crawler = _make_crawler({"BEEP_FAILURE_SOUND": "/tmp/custom_failure.aiff"})
        ext = BeepExtension.from_crawler(crawler)
        spider = _make_spider(crawler, items=0)

        ext.spider_closed(spider, reason="finished")

        mock_play.assert_called_once_with("/tmp/custom_failure.aiff")


class TestPlay:
    def test_none_sound_is_noop(self):
        BeepExtension._play(None)  # should not raise

    def test_empty_string_is_noop(self):
        BeepExtension._play("")  # should not raise

    @patch("subprocess.run")
    def test_macos_calls_afplay(self, mock_run):
        with patch.object(sys, "platform", "darwin"):
            BeepExtension._play("/path/to/success.wav")
        mock_run.assert_called_once_with(["afplay", "/path/to/success.wav"], check=False)

    @patch("subprocess.run")
    def test_linux_calls_aplay(self, mock_run):
        with patch.object(sys, "platform", "linux"):
            BeepExtension._play("/path/to/success.wav")
        mock_run.assert_called_once_with(["aplay", "/path/to/success.wav"], check=False)


class TestAddon:
    def test_registers_extension(self):
        settings = Settings()
        Addon().update_settings(settings)
        assert "scrapy_beep.extension.BeepExtension" in settings.getwithbase("EXTENSIONS")

    def test_extension_priority(self):
        settings = Settings()
        Addon().update_settings(settings)
        assert settings.getwithbase("EXTENSIONS")["scrapy_beep.extension.BeepExtension"] == 500


class TestBundledSounds:
    def test_bundled_sounds_exist(self):
        from scrapy_beep.extension import _DEFAULT_SUCCESS, _DEFAULT_FAILURE
        import pathlib
        assert pathlib.Path(_DEFAULT_SUCCESS).exists(), "success.wav missing from package"
        assert pathlib.Path(_DEFAULT_FAILURE).exists(), "failure.wav missing from package"

    def test_defaults_used_when_no_override(self):
        from scrapy_beep.extension import _DEFAULT_SUCCESS, _DEFAULT_FAILURE
        crawler = _make_crawler()
        ext = BeepExtension.from_crawler(crawler)
        assert ext.success_sound == _DEFAULT_SUCCESS
        assert ext.failure_sound == _DEFAULT_FAILURE
