django-radius
=============

django-radius enables you to authenticate your Django users against one or many
RADIUS servers easily.

RADIUS Authentication Backend
-----------------------------

The standard RADIUS backend (`radiusauth.backends.RADIUSBackend`) allows you to
authenticate against a single RADIUS server easily, and is used by adding it to
the `AUTHENTICATION_BACKENDS` parameter in your project's settings file:

    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'radiusauth.backends.RADIUSBackend',
    )

This will first attempt to authenticate a user with the traditional Django
model-based system, and failing that, the RADIUS server.

The RADIUS server is specified in the settings file also, with the following
parameters:

    RADIUS_SERVER = 'localhost'
    RADIUS_PORT = 1812
    RADIUS_SECRET = 'S3kr3T'

This is the quickest and easiest way to enable simple, single-server RADIUS
authentication for your Django project.

Realm-Based RADIUS Authentication for Multiple RADIUS Servers
-------------------------------------------------------------

For a more advanced system, you might want to authenticate users with different
RADIUS servers, depending upon some arbitrary condition.

This might seem contrived, but the idea is to separate "realms" of users by,
for example, the URL they access your project with. People browsing to
http://client1.myproject.com might need to authenticate against one RADIUS
server, whilst people using http://client2.myproject.com might need to
authenticate against another.

The realm-based RADIUS authentication backend
(`radiusauth.backends.RADIUSRealmBackend`) expects the username to be in
a particular format: `<username>@<realm>`. The username and realm are
separated, and the realm is used to determine which RADIUS server to
authenticate against.

### Customised Functionality

The `get_server` method of the backend class is used to determine which RADIUS
server to authenticate against. This can be customised by extending the
`RADIUSRealmBackend` class, and implementing this method. `get_server` takes
one argument: the realm which was extracted from the username.

By default, the `RADIUSRealmBackend` simply returns the RADIUS server details
specified in the project's settings file.

To use your customised version of the `RADIUSRealmBackend`, just specify it in
your settings file as above:

    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'myproject.users.MyRADIUSBackend',
    )
