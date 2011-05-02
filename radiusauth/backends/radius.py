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

class RADIUSBackend(object):
    """
    Authenticate against a RADIUS server, specified by the following settings:

        RADIUS_SERVER
        RADIUS_PORT
        RADIUS_SECRET

    The `authenticate' method returns None if an error occurs, so as to allow
    the authentication system to move on to the next backend instead of
    throwing an exception.

    Based on code from koansys-django-authradius:
        http://code.google.com/p/koansys-django-authradius/
    """
    supports_anonymous_user = False
    supports_object_permissions = False

    def _get_dictionary(self):
        return Dictionary(StringIO(DICTIONARY))

    def _get_auth_packet(self, username, password, client):
        pkt = client.CreateAuthPacket(code=AccessRequest,
                                      User_Name=username)
        pkt["User-Password"] = pkt.PwCrypt(password)
        return pkt

    def _parse_username(self, username):
        """
        Get the server details to use for a given username, assumed to be in
        the format <username@realm>.
        """
        user, _, realm = username.rpartition(REALM_SEPARATOR)
        if not user:
            return (username, None)
        return (user, realm)


    def get_server(self, realm):
        """
        Get the RADIUS server details for the given realm.
        """
        return (
            settings.RADIUS_SERVER,
            settings.RADIUS_PORT,
            settings.RADIUS_SECRET
        )

    def authenticate(self, username, password):
        """
        Check username against RADIUS server and return a User object or None.
        """
        user, realm = self._parse_username(username)

        if not realm:
            return None

        server = self.get_server(realm)

        if not server:
            return None

        client = Client(server=server[0],
                        authport=server[1],
                        secret=server[2],
                        dict=Dictionary(StringIO(DICTIONARY)),
                       )

        user = user.encode('utf-8')
        password = password.encode('utf-8')

        packet = self._get_auth_packet(user, password, client)

        logging.debug("Sending RADIUS authentication packet: %s" % packet)

        try:
            reply = client.SendPacket(packet)
        except Timeout, e:
            logging.error("RADIUS timeout occurred contacting %s:%s" % \
                          (server[0], server[1])
                         )
            return None
        except Exception, e:
            logging.error("RADIUS error: %s" % e)
            return None

        if reply.code == AccessReject:
            logging.warning("RADIUS access rejected for user '%s'" % username)
            return None
        elif reply.code != AccessAccept:
            logging.error("RADIUS access error for user '%s' (code %s)" % \
                          (username, reply.code)
                         )
            return None

        logging.info("RADIUS access granted for user '%s'" % username)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username)

        user.set_password(password)
        user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
