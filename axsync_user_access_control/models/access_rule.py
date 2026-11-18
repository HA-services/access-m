# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AxsyncAccessMixin(models.AbstractModel):
    """Clears the access profile cache whenever a rule or one of its lines changes."""
    _name = 'axsync.access.mixin'
    _description = 'AXSync Access Cache Mixin'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res


class AxsyncAccessRule(models.Model):
    _name = 'axsync.access.rule'
    _inherit = ['axsync.access.mixin']
    _description = 'Access Control Rule'
    _order = 'name, id'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Internal Note')
    user_ids = fields.Many2many(
        'res.users', 'axsync_access_rule_user_rel', 'rule_id', 'user_id', string='Users',
        help='Users this rule applies to.')
    group_ids = fields.Many2many(
        'res.groups', 'axsync_access_rule_group_rel', 'rule_id', 'group_id', string='User Groups',
        help='Everyone who belongs to one of these groups is also restricted by this rule.')
    company_ids = fields.Many2many(
        'res.company', 'axsync_access_rule_company_rel', 'rule_id', 'company_id', string='Companies',
        help='The rule is active only while one of these companies is the current company of the user. '
             'Leave empty to apply the rule in every company.')
    user_count = fields.Integer(compute='_compute_user_count', string='Users Affected')

    # Whole-user switches
    read_only_user = fields.Boolean(
        string='Read-Only User',
        help='The user can read everything they could before but cannot create, edit or delete any record.')
    disable_debug = fields.Boolean(
        string='Disable Developer Mode', help='The debug (developer) mode is switched off for the user.')
    disable_login = fields.Boolean(
        string='Disable Login', help='The user cannot log in and an open session is ended.')
    hide_apps_menu = fields.Boolean(string='Hide the Apps Menu Button')

    # Global switches (all models)
    hide_chatter = fields.Boolean(string='Hide Chatter Everywhere')
    hide_send_message = fields.Boolean(string='Hide Send Message')
    hide_log_note = fields.Boolean(string='Hide Log Note')
    hide_activity = fields.Boolean(string='Hide Schedule Activity')
    hide_import = fields.Boolean(string='Hide Import Everywhere')
    hide_export = fields.Boolean(string='Hide Export Everywhere')
    hide_add_property = fields.Boolean(string='Hide Add Property')
    hide_filter_button = fields.Boolean(string='Hide the Filter Dropdown Button')
    hide_custom_filter = fields.Boolean(string='Hide Add Custom Filter')
    hide_custom_group = fields.Boolean(string='Hide Add Custom Group')

    menu_ids = fields.Many2many(
        'ir.ui.menu', 'axsync_access_rule_menu_rel', 'rule_id', 'menu_id', string='Hidden Menus',
        help='Menus (and everything below them) the restricted users do not see.')

    model_line_ids = fields.One2many('axsync.access.model.line', 'rule_id', string='Model Access')
    field_line_ids = fields.One2many('axsync.access.field.line', 'rule_id', string='Field Access')
    domain_line_ids = fields.One2many('axsync.access.domain.line', 'rule_id', string='Record Access')
    element_line_ids = fields.One2many('axsync.access.element.line', 'rule_id', string='Buttons, Tabs and Filters')

    @api.depends('user_ids', 'group_ids')
    def _compute_user_count(self):
        for rule in self:
            users = rule.user_ids
            if rule.group_ids:
                users |= self.env['res.users'].sudo().search([('groups_id', 'in', rule.group_ids.ids)])
            rule.user_count = len(users)

    @api.constrains('name', 'user_ids', 'group_ids')
    def _check_targets(self):
        for rule in self:
            if not rule.user_ids and not rule.group_ids:
                raise ValidationError(_('Select at least one user or one user group for the rule "%s".', rule.name))


class AxsyncAccessModelLine(models.Model):
    _name = 'axsync.access.model.line'
    _inherit = ['axsync.access.mixin']
    _description = 'Access Control Model Line'
    _rec_name = 'model_id'

    rule_id = fields.Many2one('axsync.access.rule', required=True, ondelete='cascade', index=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade',
                               domain=[('transient', '=', False)])
    model_name = fields.Char(string='Model Name', related='model_id.model', store=True, index=True)

    hide_create = fields.Boolean(string='Create')
    hide_edit = fields.Boolean(string='Edit')
    hide_delete = fields.Boolean(string='Delete')
    hide_archive = fields.Boolean(string='Archive')
    hide_duplicate = fields.Boolean(string='Duplicate')
    hide_export = fields.Boolean(string='Export')
    hide_import = fields.Boolean(string='Import')
    hide_add_property = fields.Boolean(string='Add Property')
    read_only = fields.Boolean(string='Read-Only Model', help='Nothing can be created, edited or deleted on this model.')

    hide_chatter = fields.Boolean(string='Chatter')
    hide_send_message = fields.Boolean(string='Send Message')
    hide_log_note = fields.Boolean(string='Log Note')
    hide_activity = fields.Boolean(string='Schedule Activity')

    hide_view_list = fields.Boolean(string='List')
    hide_view_kanban = fields.Boolean(string='Kanban')
    hide_view_pivot = fields.Boolean(string='Pivot')
    hide_view_graph = fields.Boolean(string='Graph')
    hide_view_calendar = fields.Boolean(string='Calendar')
    hide_view_activity = fields.Boolean(string='Activity')
    hide_view_map = fields.Boolean(string='Map')

    hide_report_ids = fields.Many2many(
        'ir.actions.report', 'axsync_access_model_report_rel', 'line_id', 'report_id', string='Hidden Reports')
    hide_action_ids = fields.Many2many(
        'ir.actions.server', 'axsync_access_model_action_rel', 'line_id', 'action_id', string='Hidden Server Actions')
    hide_window_action_ids = fields.Many2many(
        'ir.actions.act_window', 'axsync_access_model_winaction_rel', 'line_id', 'action_id',
        string='Hidden Window Actions')


class AxsyncAccessFieldLine(models.Model):
    _name = 'axsync.access.field.line'
    _inherit = ['axsync.access.mixin']
    _description = 'Access Control Field Line'
    _rec_name = 'model_id'

    rule_id = fields.Many2one('axsync.access.rule', required=True, ondelete='cascade', index=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade',
                               domain=[('transient', '=', False)])
    model_name = fields.Char(string='Model Name', related='model_id.model', store=True, index=True)
    field_ids = fields.Many2many(
        'ir.model.fields', 'axsync_access_field_line_field_rel', 'line_id', 'field_id', string='Fields',
        domain="[('model_id', '=', model_id)]")
    invisible = fields.Boolean(string='Invisible')
    readonly = fields.Boolean(string='Read-Only')
    required = fields.Boolean(string='Required')
    no_open = fields.Boolean(string='Remove External Link', help='Removes the arrow that opens the linked record.')
    no_create = fields.Boolean(string='No Create', help='Removes "Create" from the dropdown of a relational field.')
    no_create_edit = fields.Boolean(string='No Create and Edit', help='Removes "Create and Edit..." from the dropdown.')
    hide_in_kanban = fields.Boolean(string='Hide in Kanban Cards')
    no_export = fields.Boolean(string='Not Exportable')
    condition_domain = fields.Char(
        string='Only When',
        help='Optional condition on the record, for example [("state", "=", "done")]. When set, Invisible, '
             'Read-Only and Required apply only to records that match. Fields of the same model only.')
    enforce_server = fields.Boolean(
        string='Also Enforce on the Server',
        help='Read-Only: reject writes that change these fields. Required: reject saves where they are empty. '
             'Applies only when no condition is set.')

    @api.constrains('field_ids', 'model_id')
    def _check_fields_model(self):
        for line in self:
            if line.field_ids.filtered(lambda f: f.model_id != line.model_id):
                raise ValidationError(_('All fields must belong to the model %s.', line.model_id.display_name))

    @api.constrains('condition_domain')
    def _check_condition(self):
        engine = self.env['axsync.access.engine']
        for line in self:
            if line.condition_domain:
                try:
                    engine.domain_to_expression(line.condition_domain, {'uid': self.env.uid})
                except Exception as exc:
                    raise ValidationError(_('The condition is not supported: %s', exc)) from exc


class AxsyncAccessDomainLine(models.Model):
    _name = 'axsync.access.domain.line'
    _inherit = ['axsync.access.mixin']
    _description = 'Access Control Record Line'
    _rec_name = 'model_id'

    rule_id = fields.Many2one('axsync.access.rule', required=True, ondelete='cascade', index=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade',
                               domain=[('transient', '=', False)])
    model_name = fields.Char(string='Model Name', related='model_id.model', store=True, index=True)
    domain = fields.Char(
        string='Records the User Can Access', default='[]',
        help='Only records matching this domain are accessible for the operations ticked below. '
             'You can use user.id, uid, company_id and context_today() in the domain.')
    apply_read = fields.Boolean(string='Read', default=True)
    apply_write = fields.Boolean(string='Edit', default=True)
    apply_create = fields.Boolean(string='Create', default=True)
    apply_unlink = fields.Boolean(string='Delete', default=True)
    hierarchy = fields.Boolean(
        string='Own and Subordinates',
        help='Restricts to records whose user field points to the user or to someone who reports to the user '
             '(see the Reports To field on the user form).')
    hierarchy_field_id = fields.Many2one(
        'ir.model.fields', string='User Field', domain="[('model_id', '=', model_id), ('relation', '=', 'res.users'), "
                                                       "('ttype', '=', 'many2one')]")

    @api.constrains('hierarchy', 'hierarchy_field_id')
    def _check_hierarchy(self):
        for line in self:
            if line.hierarchy and not line.hierarchy_field_id:
                raise ValidationError(_('Choose the user field used for the hierarchy.'))

    @api.constrains('domain')
    def _check_domain(self):
        engine = self.env['axsync.access.engine']
        for line in self:
            try:
                engine.eval_domain(line.domain or '[]', self.env.user)
            except Exception as exc:
                raise ValidationError(_('The domain is not valid: %s', exc)) from exc


class AxsyncAccessItem(models.Model):
    """A button, tab, filter or group-by option found in the views of a model."""
    _name = 'axsync.access.item'
    _description = 'Access Control View Element'
    _order = 'model_name, kind, label, name'

    model_name = fields.Char(required=True, index=True)
    kind = fields.Selection([('button', 'Button'), ('tab', 'Tab'), ('filter', 'Filter'), ('group_by', 'Group By')],
                            required=True)
    name = fields.Char()
    label = fields.Char()

    @api.depends('name', 'label', 'kind')
    def _compute_display_name(self):
        for item in self:
            item.display_name = '%s (%s)' % (item.label or item.name or '?', item.name) if item.label and item.name \
                else (item.label or item.name or '?')

    @api.model
    def scan_model(self, model_name):
        """Read the views of a model and register their buttons, tabs, filters and group-by options."""
        if model_name not in self.env:
            return self.browse()
        Model = self.env[model_name]
        found = {}
        view_types = ['form', 'tree', 'kanban', 'search']
        arches = []
        for vtype in view_types:
            try:
                arches.append(Model.get_view(None, vtype)['arch'])
            except Exception:
                continue
        views = self.env['ir.ui.view'].sudo().search([('model', '=', model_name), ('mode', '=', 'primary'),
                                                      ('type', 'in', view_types)])
        for view in views:
            try:
                arches.append(Model.get_view(view.id, view.type)['arch'])
            except Exception:
                continue
        for arch in arches:
            try:
                root = etree.fromstring(arch.encode())
            except Exception:
                continue
            for node in root.iter('button', 'a', 'page', 'filter'):
                if not isinstance(node.tag, str):
                    continue
                name = node.get('name') or ''
                label = (node.get('string') or ''.join(node.itertext())).strip()[:120]
                if node.tag == 'page':
                    kind = 'tab'
                elif node.tag == 'filter':
                    kind = 'group_by' if 'group_by' in (node.get('context') or '') else 'filter'
                elif node.tag == 'button' or node.get('type') in ('object', 'action'):
                    kind = 'button'
                else:
                    continue
                if not name and not label:
                    continue
                found[(kind, name, label)] = True
        existing = {(i.kind, i.name or '', i.label or '') for i in self.sudo().search([('model_name', '=', model_name)])}
        vals = [{'model_name': model_name, 'kind': k, 'name': n, 'label': l}
                for (k, n, l) in found if (k, n, l) not in existing]
        if vals:
            self.sudo().create(vals)
        return self.sudo().search([('model_name', '=', model_name)])


class AxsyncAccessElementLine(models.Model):
    _name = 'axsync.access.element.line'
    _inherit = ['axsync.access.mixin']
    _description = 'Access Control Element Line'
    _rec_name = 'model_id'

    rule_id = fields.Many2one('axsync.access.rule', required=True, ondelete='cascade', index=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade',
                               domain=[('transient', '=', False)])
    model_name = fields.Char(string='Model Name', related='model_id.model', store=True, index=True)
    kind = fields.Selection([('button', 'Buttons'), ('tab', 'Tabs'), ('filter', 'Filters'),
                             ('group_by', 'Group By Options')], string='Type', required=True, default='button')
    item_ids = fields.Many2many(
        'axsync.access.item', 'axsync_access_element_line_item_rel', 'line_id', 'item_id', string='Hidden Elements',
        domain="[('model_name', '=', model_name), ('kind', '=', kind)]")
    condition_domain = fields.Char(
        string='Only When',
        help='Optional condition on the record. When set, buttons and tabs are hidden only for records '
             'that match. Fields of the same model only.')

    @api.constrains('condition_domain')
    def _check_condition(self):
        engine = self.env['axsync.access.engine']
        for line in self:
            if line.condition_domain:
                try:
                    engine.domain_to_expression(line.condition_domain, {'uid': self.env.uid})
                except Exception as exc:
                    raise ValidationError(_('The condition is not supported: %s', exc)) from exc

    def action_scan(self):
        """Load the elements of the model so they can be selected."""
        for line in self:
            self.env['axsync.access.item'].scan_model(line.model_name)
        return True

    @api.onchange('model_id', 'kind')
    def _onchange_model_id(self):
        if self.model_id:
            self.env['axsync.access.item'].scan_model(self.model_id.model)
        self.item_ids = False
