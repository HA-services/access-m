# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models
from odoo.exceptions import AccessError


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            engine = self.env['axsync.access.engine']
            if engine.is_active():
                for vals in vals_list:
                    if vals.get('message_type') != 'comment' or not vals.get('model'):
                        continue
                    subtype = self.env['mail.message.subtype'].sudo().browse(vals['subtype_id']) \
                        if vals.get('subtype_id') else self.env['mail.message.subtype']
                    kind = 'note' if subtype and subtype.internal else 'send'
                    if engine.chatter_blocked(vals['model'], kind):
                        raise AccessError(_('You are not allowed to post messages or notes on this document.'))
        return super().create(vals_list)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            engine = self.env['axsync.access.engine']
            if engine.is_active():
                for vals in vals_list:
                    model = vals.get('res_model')
                    if not model and vals.get('res_model_id'):
                        model = self.env['ir.model'].sudo().browse(vals['res_model_id']).model
                    if model and engine.chatter_blocked(model, 'activity'):
                        raise AccessError(_('You are not allowed to schedule activities on this document.'))
        return super().create(vals_list)
