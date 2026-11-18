# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = 'res.users'

    axsync_manager_id = fields.Many2one(
        'res.users', string='Reports To', copy=False, index=True,
        help='Used by the "Own and Subordinates" option of User Access Control record rules.')

    def _axsync_login_disabled(self):
        """True when an access control rule disables the login of this user."""
        self.ensure_one()
        user = self.sudo()
        engine = self.env['axsync.access.engine'].sudo()
        company_ids = {user.company_id.id, *user.company_ids.ids}
        return any(engine._profile(user.id, company_id)['global'].get('login_off') for company_id in company_ids)

    def _check_credentials(self, *args, **kwargs):
        res = super()._check_credentials(*args, **kwargs)
        if self._axsync_login_disabled():
            raise AccessDenied(_('Your login has been disabled by an administrator.'))
        return res

    @api.model
    def has_group(self, group_ext_id):
        uid = self.id or self.env.uid
        if group_ext_id == 'base.group_allow_export' and uid == self.env.uid and not self.env.su:
            if self.env['axsync.access.engine'].profile()['global'].get('export'):
                return False
        return super().has_group(group_ext_id)
