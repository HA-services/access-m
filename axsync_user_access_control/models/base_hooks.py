# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        return self.env['axsync.access.engine'].postprocess_view(self._name, result)

    def read(self, fields=None, load='_classic_read'):
        result = super().read(fields, load)
        if self.env.su:
            return result
        return self.env['axsync.access.engine'].blank_hidden(self._name, result)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.su:
            self.env['axsync.access.engine'].check_required(records, creating=True)
        return records

    def write(self, vals):
        if not self.env.su and vals:
            self.env['axsync.access.engine'].check_write(self._name, vals)
        res = super().write(vals)
        if not self.env.su and vals:
            self.env['axsync.access.engine'].check_required(self, vals)
        return res

    def copy(self, default=None):
        if not self.env.su:
            self.env['axsync.access.engine'].check_duplicate(self._name)
        return super().copy(default)

    def export_data(self, fields_to_export):
        if not self.env.su:
            self.env['axsync.access.engine'].check_export(self._name, fields_to_export)
        return super().export_data(fields_to_export)

    @api.model
    def load(self, fields, data):
        if not self.env.su:
            self.env['axsync.access.engine'].check_import(self._name)
        return super().load(fields, data)
