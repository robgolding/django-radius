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

    def __init__(self, server=None, port=None, secret=None):
        self.server = server
        self.port = port
        self.secret = secret

        if self.server is None:
            self.server = settings.RADIUS_SERVER
        if self.port is None:
            self.port = settings.RADIUS_PORT
        if self.secret is None:
            self.secret = settings.RADIUS_SECRET
        self.secret.encode('utf-8')

        self.client = Client(server=self.server,
                             authport=self.port,
                             secret=self.secret,
                             dict=Dictionary(StringIO(DICTIONARY)),
                            )

    def _get_dictionary(self):
        return Dictionary(StringIO(DICTIONARY))

    def _get_auth_packet(self, username, password):
        pkt = self.client.CreateAuthPacket(code=AccessRequest,
                                           User_Name=username)
        pkt["User-Password"] = pkt.PwCrypt(password)
        return pkt

    def authenticate(self, username, password):
        """
        Check username against RADIUS server and return a User object or None.
        """
        username = username.encode('utf-8')
        password = password.encode('utf-8')

        packet = self._get_auth_packet(username, password)

        logging.debug("Sending RADIUS authentication packet: %s" % packet)

        try:
            reply = self.client.SendPacket(packet)
        except Timeout, e:
            logging.error("RADIUS timeout occurred contacting %s:%s" % \
                          (self.server, self.port)
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
            user.set_unusable_password()
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
