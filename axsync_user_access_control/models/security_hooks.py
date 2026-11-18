# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
# Odoo 20: model access and record rules are merged into ir.access, enforced by BaseModel._access_domain.
from odoo import api, models
from odoo.fields import Domain

from . import domain_utils


class BaseAccess(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _access_domain(self, operation):
        domain = super()._access_domain(operation)
        if self.env.su or domain.is_false():
            return domain
        engine = self.env['axsync.access.engine']
        if engine.is_blocked(self._name, operation):
            return Domain.FALSE
        extra = engine.extra_domain(self._name, operation)
        if not extra:
            return domain
        return domain & Domain(domain_utils.normalize_domain(extra))
