# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
""" Test helpers
"""
from collections import defaultdict


def _int2status(status):
    if status == 200:
        return '200 OK'
    if status == 400:
        return '400 Bad Request'
    if status == '401':
        return '400 Unauthorized'

    return '%d Explanation' % status


class ClientTesterMiddleware(object):
    """Middleware that let a client drive failures for testing purposes.

    The client sends POST requests with the desired status code, e.g.:

        /__testing__/503
        /__testing__/400

    Everytime such a call is made, it's appended to an list. The next
    call by the same client IP will result in a replay of the list,
    until it's empty.

    Optionally, the body may contain the body to send back.
    """
    def __init__(self, app, path='/__testing__'):
        self.app = app
        self.path = path
        self.replays = defaultdict(list)

    def _get_client_ip(self, environ):
        if 'HTTP_X_FORWARDED_FOR' in environ:
            return environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()

        if 'REMOTE_ADDR' in environ:
            return environ['REMOTE_ADDR']

        return None

    def _resp(self, sr, status, body='', ctype='text/plain'):
        headers = [('Content-Type', ctype)]
        sr(status, headers)
        return [body]

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        client_ip = self._get_client_ip(environ)
        replays = self.replays[client_ip]

        if not path.startswith(self.path):
            # do we have something to replay ?
            if len(replays) > 0:
                # yes
                status, body = replays.pop()
                status = _int2status(status)
                return self._resp(start_response, status, body)
            else:
                # no, regular app
                return self.app(environ, start_response)

        # that's something to add to the pile
        try:
            status = int(path.split('/')[-1])
        except TypeError:
            return self._resp(start_response, '400 Bad Request')

        body = environ['wsgi.input'].read()
        replays.insert(0, (status, body))
        return self._resp(start_response, '200 OK')
