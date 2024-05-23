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

You may optionally accept whether the user is a staff or superuser from the
remote radius server with the following option. If not set, it will default
to `True`, as django-radius has functioned in earlier versions.

```python
RADIUS_REMOTE_ROLES = True
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
(`radiusauth.backends.RADIUSRealmBackend`) expects to be provided with an extra
argument when authenticating a user: the realm in which they belong.
The realm is used to determine which RADIUS server to contact when verifying
the user's credentials - though this logic is up to the developer to implement
by overriding the `get_server` method.

As with the standard RADIUS backend, a `User` object is created in the Django
auth application when a user successfully logs into the system. With the
realm-based backend, however, the username is set to the string returned by the
`construct_full_username` method, which is supplied with the username and the
realm. By default, this method returns a string in the format
<username>@<realm> to avoid clashes in the Django user database. You should be
aware of this fact when displaying usernames in templates etc., as users might
be confused by a username which looks similar to an email address, but is
clearly not.

### Customised Functionality

The `get_server` method of the backend class is used to determine which RADIUS
server to authenticate against. This can be customised by extending the
`RADIUSRealmBackend` class, and implementing this method. `get_server` takes
one argument: the realm which is passed to the `authenticate` method.

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

class MyRADIUSBackend(RADIUSRealmBackend):
    def get_server(self, realm):
        if realm in RADIUS_SERVERS:
            return RADIUS_SERVERS[realm]
        return None
```

`myproject/users/forms.py`

```python
from django import forms

from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm

class RADIUSAuthenticationForm(AuthenticationForm):
    def __init__(self, realm, request, *args, **kwargs):
        super(UserAuthenticationForm, self).__init__(request, *args, **kwargs)
        self.realm = realm

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if self.realm and username and password:
            self.user_cache = authenticate(realm=self.realm,
                                           username=username,
                                           password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Please enter a correct username and password. '
                    'Note that both fields are case-sensitive.')
            elif not self.user_cache.is_active:
                raise forms.ValidationError('This account is inactive.')
        self.check_for_test_cookie()
        return self.cleaned_data

    def get_user(self):
        return self.user_cache
```

`myproject/users/urls.py`

```python
from django.conf.urls.defaults import patterns, url

from myproject.users.forms import RADIUSAuthenticationForm

urlpatterns = patterns('django.contrib.auth.views',

    url(r'^login/$', 'login',
        {'authentication_form': RADIUSAuthenticationForm},
        name='radius_login'),

)
```

`myproject/settings.py`

```python
...
AUTHENTICATION_BACKENDS = (
    'myproject.users.backends.MyRADIUSBackend',
    'django.contrib.auth.backends.ModelBackend',
)
...
```

The custom authentication form above is then instantiated with a `realm`
argument (determined by some other means) which is then passed to Django's
`authenticate` method. The `RADIUSRealmBackend` can then use this value to
determine which RADIUS server to use when validating the user's credentials.

Additional Attributes
---------------------

The RADIUS authentication packet contains the following attributes by default:

* `User-Name` (the user's username)
* `User-Password` (the user's password)
* `NAS-Identifier` (`django-radius`)

To set additional attributes, use the `RADIUS_ATTRIBUTES` setting:

```python
...
RADIUS_ATTRIBUTES = {
    "NAS-IP-Address": "192.168.1.10",
    "NAS-Port": 0,
    "Service-Type": "Login-User",
}
...
```

RADIUS attribute types 1-39 are supported. See the [Radius Types][types]
IANA page for details.

[types]: http://www.iana.org/assignments/radius-types/radius-types.xhtml

Group Mapping
---------------------

The authentication backend allows you to map RADIUS Attribute 25 "Class" 
(See [Radius Types][types]) in the RADIUS Server Reply to the User's 
is_staff and is_superuser properties and to the groups the User belongs to.

For each role (is_staff and is_superuser) and group mapping one RAIDUS Attribute 
25 "Class" AVP has to be returned by the RADIUS Server.

The syntax allows the following mappings:
* `role=staff` (sets is_staff=True in the User object)
* `role=superuser` (sets is_superuser=True for the User object)
* `role=su-staff` (sets both is_superuser and is_staff = True for the User object)
* `group=Group1` (add the User object to `Group1`)

To avoid namespace clashes in the RADIUS Attribute 25 values that may be
used by other applications, a prefix can be configured in the Django project's
settings.py for the values returned by the RADIUS server in the Attribute 25
"Class" AVP:

```python
RADIUS_CLASS_APP_PREFIX = 'someprojectname'
```

This will make the app look for `someprojectnamerole=` and `someprojectnamegroup=`
when parsing through the Attribute 25 "Class" AVP and ignore other returned values.
