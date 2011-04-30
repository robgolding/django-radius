django-radius
=============

django-radius enables you to authenticate your Django users against one or many
RADIUS servers.

RADIUS Authentication Backend
-----------------------------

The RADIUS backend allows you to hook into Django's authentication backends
system in your settings.py file:

    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'radiusauth.backends.RADIUSBackend',
    )

This will first attempt to authenticate a user with the traditional Django
model-based system, and failing that, the RADIUS server. In this instance, the
RADIUS server is specified in settings.py also:


RADIUS_SERVER = 'localhost'
RADIUS_PORT = 1812
RADIUS_SECRET = 'S3kr3T'

Note that this only allows one RADIUS server to be configured, and is the
simplest way to enable RADIUS authentication.

RADIUS Authentication Form & Multiple RADIUS Servers
----------------------------------------------------

django-radius also comes with a modified `login' view and authentication form,
for use with a specialised RADIUS setup. This allows you to use a different
RADIUS server to authenticate users, depending on some value in the `request'
variable.

This might seem contrived, but the idea is to separate "realms" of users by the
URL by which they access your project. For example, people browsing to
http://client1.myproject.com might need to authenticate against one RADIUS
server, whilst http://client2.myproject.com might need to authenticate against
another.

To enable this functionality, there is no need to specify the backend in
settings.py. Instead, point your login view to 'radiusauth.views.login', like
so:

    url(r'^login/$', 'radiusauth.views.login', {
        'authentication_form': MyRADIUSAuthenticationForm,
    }

Notice that the extra variable `authentication_form' is also set. This is to
allow you to specify your own login for determining the correct RADIUS server
to use. For example:

    from radiusauth.forms import RADIUSAuthenticationForm

    class MyRADIUSAuthenticationForm(RADIUSAuthenticationForm):
        def get_radius_settings(self, request):
            if request.META['HTTP_HOST'] == 'client1.myproject.com':
                # RADIUS server details for client1
                return ('radius.client1.com', 1812, 'client1_secret')
            elif request.META['HTTP_HOST'] == 'client2.myproject.com':
                # RADIUS server details for client2
                return ('radius.client2.com', 1812, 'client2_secret')
            else:
                # RADIUS authentication not allowed otherwise
                return None

All that is required is to override the `get_radius_settings' method, and have
it return a 3-tuple containing (<hostname>, <port>, <secret>) which specifies
the server which will be used to authenticate the user.

By defauly, the RADIUSAuthenticationForm simply returns the RADIUS server
details specified in the project's settings.py.
