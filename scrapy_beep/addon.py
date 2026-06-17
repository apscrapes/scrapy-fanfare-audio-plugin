class Addon:
    def update_settings(self, settings):
        settings.set(
            "EXTENSIONS",
            {"scrapy_beep.extension.BeepExtension": 500},
            priority="addon",
        )
