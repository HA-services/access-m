# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, _, api, models
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.http.session import SessionExpiredException


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug)
        if self.env.su:
            return visible
        hidden = self.env['axsync.access.engine'].hidden_menu_ids()
        return set(visible) - hidden if hidden else visible


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def get_bindings(self, model_name):
        result = super().get_bindings(model_name)
        if self.env.su or not result:
            return result
        engine = self.env['axsync.access.engine']
        eff = engine.effective(engine.profile(), model_name)
        hidden_reports, hidden_actions = eff['reports'], eff['actions']
        if not (hidden_reports or hidden_actions):
            return result
        filtered = {}
        for kind, actions in result.items():
            hidden = hidden_reports if kind == 'report' else hidden_actions
            kept = [a for a in actions if a.get('id') not in hidden]
            if kept:
                filtered[kind] = kept
        return filtered


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        vals = super()._get_action_dict()
        # the web client builds actions through sudo(), so the real user id is what counts here
        if self.env.uid == SUPERUSER_ID:
            return vals
        engine = self.env['axsync.access.engine']
        prof = engine._profile(self.env.uid, self.env.company.id)
        if prof['active']:
            self._axsync_filter_views(vals, prof)
        return vals

    def _axsync_filter_views(self, vals, prof):
        engine = self.env['axsync.access.engine']
        model = vals.get('res_model')
        views = vals.get('views')
        if not model or not views:
            return
        hidden = engine.effective(prof, model)['views']
        if not hidden:
            return
        kept = [v for v in views if v[1] not in ('tree', 'list', 'kanban', 'pivot', 'graph', 'calendar', 'activity',
                                                 'map') or {'tree': 'list'}.get(v[1], v[1]) not in hidden]
        if not kept:
            return
        vals['views'] = kept
        modes = [v[1] for v in kept]
        vals['view_mode'] = ','.join(modes)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_debug(cls):
        super()._handle_debug()
        uid = request.session.uid
        if uid and request.session.debug:
            # routes such as /web have no user environment yet, so the session user is looked up directly
            user = request.env['res.users'].sudo().browse(uid)
            if user.exists():
                engine = request.env['axsync.access.engine'].sudo()
                if engine._profile(uid, user.company_id.id)['global'].get('debug_off'):
                    request.session.debug = ''

    @classmethod
    def _authenticate(cls, endpoint):
        res = super()._authenticate(endpoint)
        if request.session.uid and request.env.uid:
            env = request.env(su=False)
            user = env.user
            if user.exists() and user._axsync_login_disabled():
                request.session.logout(keep_db=True)
                raise SessionExpiredException('Your login has been disabled by an administrator.')
        return res

    def session_info(self):
        result = super().session_info()
        if request.session.uid:
            flags = request.env(su=False)['axsync.access.engine'].session_flags()
            if flags:
                result['axsync_access'] = flags
        return result


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        self._axsync_check_report(report_ref)
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    @api.model
    def _axsync_check_report(self, report_ref):
        if self.env.su:
            return
        engine = self.env['axsync.access.engine']
        prof = engine.profile()
        if not prof['active']:
            return
        report = self._get_report(report_ref)
        eff = engine.effective(prof, report.model)
        if report.id in eff['reports']:
            raise AccessError(_('You are not allowed to print this report.'))
