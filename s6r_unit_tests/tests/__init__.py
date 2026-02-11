# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

# in v18+, trying to import odoo.tests when test_enable is False will print a logger.error
from odoo.tools import config
if config['test_enable']:
    from . import runner
    from . import loader
    from . import common
    from . import test_patch_invisible_fields