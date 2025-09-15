# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from . import models
from odoo.tools.config import config
if config['test_enable'] or config['test_file']:
    from . import tests
