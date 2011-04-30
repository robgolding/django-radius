from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _

from radiusauth.backends import RADIUSBackend

class RADIUSAuthenticationForm(AuthenticationForm):
    """
    RADIUS authentication form. Same as the base django.contrib.auth
    AuthenticationForm, except that the user is authenticated agains the
    RADIUSAuthenticationBackend *only* (rather than using the
    AUTHENTICATION_BACKENDS setting). A request object is required on every
    initialization (used for figuring out which RADIUS server to use).
    """
    def __init__(self, request=None, *args, **kwargs):
        """
        We need a request object to get the RADIUS settings, so require that it
        is specified every time the form is initialized (unlike the base
        AuthenticationForm, where it's optional.
        """
        if request is None:
            raise TypeError('RADIUSAuthenticationForm must be initialized'
                            ' with a request object')
        radius_settings = self.get_radius_settings(request)
        self.auth_backend = RADIUSBackend(*radius_settings)
        super(RADIUSAuthenticationForm, self).__init__(request, *args, **kwargs)

    def get_radius_settings(self, request):
        """
        Get the RADIUS settings to use for the given request. By default this
        just returns the settings specified in settings file. Override to
        provide a more intelligent method.

        Returns a 3-tuple (<server>, <port>, <secret>).
        """
        return (
            settings.RADIUS_SERVER,
            settings.RADIUS_PORT,
            settings.RADIUS_SECRET
        )

    def clean(self):
        """
        A slight modification to the default Django behaviour, using *only*
        the RADIUSAuthenticationBackend to authenticate the user, via the server
        specified by the `get_radius_settings` method of this class (or
        subclass).
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            user = self.auth_backend.authenticate(username=username,
                                                  password=password)
            self.user_cache = user
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct username and password. Note that both fields are case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))
        self.check_for_test_cookie()
        return self.cleaned_data
