# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo.tools import config
if config['test_enable']:
    import re
    import copy
    from odoo.tests.common import ChromeBrowser
    _handle_console_origin = ChromeBrowser._handle_console
    _handle_exception_origin = ChromeBrowser._handle_exception


def get_console_message_to_skip(self):
    """
    Returns a list of dict of excluded Chrome browser console messages.
    [
        {'type': 'warning',
         'msg': 'Smartlook is stopped'},
    ]
    """
    return []

if config['test_enable']:
    ChromeBrowser.get_console_message_to_skip = get_console_message_to_skip


def get_formatted_message(self, args):
    """ This is just a factorization of the beginning of the original v16 _handle_console function """
    if args:
        arg0, args = str(self._from_remoteobject(args[0])), args[1:]
    else:
        arg0, args = '', []
    formatted = [re.sub(r'%[%sdfoOc]', self.console_formatter(args), arg0)]
    formatted.extend(str(self._from_remoteobject(arg)) for arg in args)
    return ' '.join(formatted)

if config['test_enable']:
    ChromeBrowser.get_formatted_message = get_formatted_message


def _handle_console(self, type, args=None, stackTrace=None, **kw):
    for msg_to_skip in self.get_console_message_to_skip():
        if msg_to_skip['type'] == type:
            msg = self.get_formatted_message(copy.deepcopy(args))
            if msg_to_skip['msg'] in msg:
                return
    _handle_console_origin(self, type, args, stackTrace, **kw)

if config['test_enable']:
    ChromeBrowser._handle_console = _handle_console


def _handle_exception(self, exceptionDetails, timestamp):
    for msg_to_skip in self.get_console_message_to_skip():
        if msg_to_skip['type'] == 'error':
            if msg_to_skip['msg'] in exceptionDetails['text']:
                return
    _handle_exception_origin(self, exceptionDetails, timestamp)


if config['test_enable']:
    ChromeBrowser._handle_exception = _handle_exception
