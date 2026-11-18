# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
# Odoo 17 and 18: model access is checked by ir.model.access and record rules by ir.rule.
from odoo import api, models
from odoo.exceptions import AccessError
from . import domain_utils as expression


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    def check(self, model, mode='read', raise_exception=True):
        allowed = super().check(model, mode, raise_exception)
        if allowed and not self.env.su:
            engine = self.env['axsync.access.engine']
            if engine.is_blocked(model, mode):
                if raise_exception:
                    raise AccessError(engine.blocked_message(model, mode))
                return False
        return allowed


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _compute_domain(self, model_name, mode="read"):
        domain = super()._compute_domain(model_name, mode)
        if self.env.su:
            return domain
        extra = self.env['axsync.access.engine'].extra_domain(model_name, mode)
        if not extra:
            return domain
        return expression.AND([domain, extra]) if domain else extra
