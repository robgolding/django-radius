django-radius
=============

django-radius enables you to authenticate your Django users against one or many
RADIUS servers easily.

RADIUS Authentication Backend
-----------------------------

The standard RADIUS backend (`radiusauth.backends.RADIUSBackend`) allows you to
authenticate against a single RADIUS server easily, and is used by adding it to
the `AUTHENTICATION_BACKENDS` parameter in your project's settings file:

```python
AUTHENTICATION_BACKENDS = (
    'radiusauth.backends.RADIUSBackend',
    'django.contrib.auth.backends.ModelBackend',
)
```

This will first attempt to authenticate a user with the traditional Django
model-based system, and failing that, the RADIUS server.

The RADIUS server is specified in the settings file also, with the following
parameters:

```python
RADIUS_SERVER = 'localhost'
RADIUS_PORT = 1812
RADIUS_SECRET = 'S3kr3T'
```

When a user is successfully authenticated via the RADIUS backend, a `User`
object is created in Django's built-in auth application with the same username.
This user's password is set to the password which they logged into the RADIUS
server with, so that they will be able to login with their "cached"
credentials, even if the RADIUS server is down. All activity within the Django
project can then be linked to this `User` object via foreign keys etc.

This is why the `RADIUSBackend` appears *before* the Django `ModelBackend` - so
that when users change their passwords on the RADIUS system, they are still
able to login to the Django application (and their cached credentials are
updated).

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

As with thee standard RADIUS backend, a `User` object is created in the Django
auth application when a user successfully logs into the system. With the
realm-based backend, however, the username is set to the *full* string passed
to the backend (i.e. `<username>@<realm>`). This is to avoid clashes which may
occur when authenticating against more than one RADIUS server. Simply be aware
of this fact when displaying usernames in templates etc., as users might be
confused by a username which looks similar to an email address, but is clearly
not.

### Customised Functionality

The `get_server` method of the backend class is used to determine which RADIUS
server to authenticate against. This can be customised by extending the
`RADIUSRealmBackend` class, and implementing this method. `get_server` takes
one argument: the realm which was extracted from the username.

By default, the `RADIUSRealmBackend` simply returns the RADIUS server details
specified in the project's settings file.

To use your customised version of the `RADIUSRealmBackend`, just specify it in
your settings file as above:

```python
AUTHENTICATION_BACKENDS = (
    'myproject.users.MyRADIUSBackend',
    'django.contrib.auth.backends.ModelBackend',
)
```

### Example Project

Here is an example of how a project might be constructed to authenticate to two
different RADIUS servers.

`myproject/users/backends.py`

```python
from radiusauth.backends import RADIUSRealmBackend

RADIUS_SERVERS = {
    'client1.myproject.com': ('radius.client1.com', 1812, 'S3kr3T'),
    'client2.myproject.com': ('radius.client2.com', 1812, 'p@55w0Rd'),
}

class RADIUSBackend(RADIUSRealmBackend):
    def get_server(self, realm):
        if realm in RADIUS_SERVERS:
            return RADIUS_SERVERS[realm]
        return None
```

`myproject/users/views.py`

```python
from django.contrib.auth.views import login as auth_login

def login(request):
    if request.method == 'POST':
        cname = request.META.get('HTTP_HOST', None)
        if cname and request.POST.get('username', None):
            post_data = request.POST.copy()
            post_data['username'] = '%s@%s' % \
                    (request.POST['username'], cname)
            request.POST = post_data
    return auth_login(request)
```

`myproject/settings.py`

```python
...
AUTHENTICATION_BACKENDS = (
    'myproject.user.MyRADIUSBackend',
    'django.contrib.auth.backends.ModelBackend',
)
...
```

The custom login view above alters the username in the POST data, so that when
Django passes it to the authentication backend, it contains the correct value.
In this example, the realm is set to be the HTTP host header which is
determined by the URL the client uses to access the project, though this could
be anything you like.
