# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import logging
fields_logger = logging.getLogger('odoo.fields')


def get_fields_message_to_skip():
    """
    Returns a list of dict, if fields is an empty list, the message is always skipped
    fields entry contains field name like model_name.field_name

    [{
        'msg': "overrides existing selection; use selection_add instead",
        'fields': ['res.partner.my_selection_field',
                   'sale.order.other_selection_field']
    }]
    """
    return []


fields_logger.get_fields_message_to_skip = get_fields_message_to_skip
warning_origin = fields_logger.warning


def fields_warning_override(msg, *args, **kwargs):
    for msg_to_skip in fields_logger.get_fields_message_to_skip():
        if msg_to_skip['msg'] in msg:
            if not msg_to_skip.get('fields'):
                return
            for field_name in msg_to_skip['fields']:
                field = args[0]
                if args and hasattr(field, 'model_name') and hasattr(field, 'name'):
                    if field_name == '%s.%s' % (field.model_name, field.name):
                        return

    warning_origin(msg, *args, **kwargs)


fields_logger.warning = fields_warning_override
