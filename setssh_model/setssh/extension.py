from django.conf import settings
from reviewboard.extensions.base import Extension
from reviewboard.extensions.hook import NavigationBarHook
 
class SetsshExtension(Extension):
    def __init__(self, *args, **kwargs):
        super(SetsshExtension, self).__init__(*args, **kwargs)
        self.navigationbar_hook = NavigationBarHook(
            self,
            entries = [
                {
                    'label': 'Set ssh',
                    'url': settings.SITE_ROOT + 'setssh/',
                },
            ]
        )