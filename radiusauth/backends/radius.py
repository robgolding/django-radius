import logging
from StringIO import StringIO

from pyrad.packet import AccessRequest, AccessAccept, AccessReject
from pyrad.client import Client, Timeout
from pyrad.dictionary import Dictionary

from django.conf import settings
from django.contrib.auth.models import User

DICTIONARY = u"""
ATTRIBUTE User-Name     1 string
ATTRIBUTE User-Password 2 string encrypt=1
"""

REALM_SEPARATOR = '@'

def utf8_encode_args(f):
    """Decorator to encode string arguments as UTF-8"""
    def encoded(self, *args, **kwargs):
        nargs = [ arg.encode('utf-8') for arg in args ]
        nargs = []
        for arg in args:
            if isinstance(arg, basestring):
                arg = arg.encode('utf-8')
            nargs.append(arg)
        nkwargs = {}
        for key, val in kwargs.items():
            if isinstance(val, basestring):
                val = val.encode('utf-8')
            nkwargs[key] = val
        return f(self, *nargs, **nkwargs)
    return encoded

class RADIUSBackend(object):
    """
    Standard RADIUS authentication backend for Django. Uses the server details
    specified in settings.py (RADIUS_SERVER, RADIUS_PORT and RADIUS_SECRET).
    """
    supports_anonymous_user = False
    supports_object_permissions = False

    def _get_dictionary(self):
        """
        Get the pyrad Dictionary object which will contain our RADIUS user's
        attributes. Fakes a file-like object using StringIO.
        """
        return Dictionary(StringIO(DICTIONARY))

    def _get_auth_packet(self, username, password, client):
        """
        Get the pyrad authentication packet for the username/password and the
        given pyrad client.
        """
        pkt = client.CreateAuthPacket(code=AccessRequest,
                                      User_Name=username)
        pkt["User-Password"] = pkt.PwCrypt(password)
        return pkt

    def _get_client(self, server):
        """
        Get the pyrad client for a given server. RADIUS server is described by
        a 3-tuple: (<hostname>, <port>, <secret>).
        """
        return Client(server=server[0],
                      authport=server[1],
                      secret=server[2],
                      dict=self._get_dictionary(),
                     )

    def _get_server_from_settings(self):
        """
        Get the RADIUS server details from the settings file.
        """
        return (
            settings.RADIUS_SERVER,
            settings.RADIUS_PORT,
            settings.RADIUS_SECRET
        )

    def _perform_radius_auth(self, client, packet):
        """
        Perform the actual radius authentication by passing the given packet
        to the server which `client` is bound to.
        Returns True or False depending on whether the user is authenticated
        successfully.
        """
        try:
            reply = client.SendPacket(packet)
        except Timeout, e:
            logging.error("RADIUS timeout occurred contacting %s:%s" % \
                          (client.server, client.authport)
                         )
            return False
        except Exception, e:
            logging.error("RADIUS error: %s" % e)
            return False

        if reply.code == AccessReject:
            logging.warning("RADIUS access rejected for user '%s'" % \
                            packet['User-Name'])
            return False
        elif reply.code != AccessAccept:
            logging.error("RADIUS access error for user '%s' (code %s)" % \
                          (packet['User-Name'], reply.code)
                         )
            return False

        logging.info("RADIUS access granted for user '%s'" % \
                     packet['User-Name'])
        return True

    def _radius_auth(self, server, username, password):
        """
        Authenticate the given username/password against the RADIUS server
        described by `server`.
        """
        client = self._get_client(server)
        packet = self._get_auth_packet(username, password, client)
        return self._perform_radius_auth(client, packet)

    def get_django_user(self, username, password=None):
        """
        Get the Django user with the given username, or create one if it
        doesn't already exist. If `password` is given, then set the user's
        password to that (regardless of whether the user was created or not).
        """
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username)

        if password is not None:
            user.set_password(password)
            user.save()

        return user

    @utf8_encode_args
    def authenticate(self, username, password):
        """
        Check credentials against RADIUS server and return a User object or
        None.
        """
        server = self._get_server_from_settings()
        result = self._radius_auth(server, username, password)

        if result:
            return self.get_django_user(username, password)

        return None

    def get_user(self, user_id):
        """
        Get the user with the ID of `user_id`. Authentication backends must
        implement this method.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class RADIUSRealmBackend(RADIUSBackend):
    """
    Advanced realm-based RADIUS backend. Authenticates users with a username,
    password and a realm (simply a unique string). The server to authenticate
    with is defined by the result of calling get_server(realm) on an instance
    of this class.

    By default, this class uses the RADIUS server specified in the settings
    file, regardless of the realm. Subclasses should override the `get_server`
    method to provide their own logic. The method should return a 3-tuple:
    (<hostname>, <port>, <secret>).
    """
    def get_server(self, realm):
        """
        Get the details of the RADIUS server to authenticate users of the given
        realm.

        Returns a 3-tuple (<hostname>, <port>, <secret>). Base implementation
        always returns the RADIUS server specified in the main settings file,
        and should be overridden.
        """
        return self._get_server_from_settings()

    def construct_full_username(self, username, realm):
        """
        Construct a unique username for a user, given their normal username and
        realm. This is to avoid conflicts in the Django auth app, as usernames
        must be unique.

        By default, returns a string in the format <username>@<realm>.
        """
        return '%s@%s' % (username, realm)

    @utf8_encode_args
    def authenticate(self, username, password, realm):
        """
        Check credentials against the RADIUS server identified by `realm` and
        return a User object or None. If no argument is supplied, Django will
        skip this backend and try the next one (as a TypeError will be raised
        and caught).
        """
        server = self.get_server(realm)

        if not server:
            return None

        result = self._radius_auth(server, username, password)

        if result:
            full_username = self.construct_full_username(username, realm)
            return self.get_django_user(full_username, password)

        return None
