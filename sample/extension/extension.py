from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import NavigationBarHook


class SampleExtension(Extension):
    def initialize(self):
        NavigationBarHook(
            self,
            entries = [
                {
                    'label': 'An Item on Navigation Bar',
                    'url_name': 'page-name',
                },
                {
                    'label': 'Another Item on Navigation Bar',
                    'url_name': 'page-name',
                },
            ]
        )