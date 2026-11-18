# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
import datetime
import time

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.safe_eval import datetime as safe_datetime, safe_eval, time as safe_time

from . import domain_utils as expression

MANAGER_GROUP = 'axsync_user_access_control.group_axsync_access_manager'

# Models a read-only user must still be able to write: session bookkeeping, presence, notification state, personal filters.
READ_ONLY_EXEMPT = frozenset({
    'bus.presence', 'res.users.log', 'res.users.settings', 'res.device', 'res.device.log', 'mail.notification',
    'discuss.channel.member', 'mail.presence', 'ir.filters', 'mail.guest', 'ir.websocket', 'res.users.apikeys',
    'ir.attachment',
})

VIEW_TAGS = ('tree', 'list', 'form', 'kanban', 'graph', 'pivot', 'calendar', 'search', 'gantt', 'map', 'activity',
             'cohort')
LIST_TAGS = ('tree', 'list')
VIEW_TYPE_FLAGS = {
    'tree': 'list', 'list': 'list', 'kanban': 'kanban', 'pivot': 'pivot', 'graph': 'graph', 'calendar': 'calendar',
    'activity': 'activity', 'map': 'map',
}

MODEL_FLAGS = ('create', 'edit', 'delete', 'archive', 'duplicate', 'export', 'import', 'add_property', 'read_only',
               'chatter', 'send', 'note', 'activity')
GLOBAL_FLAGS = ('read_only', 'debug_off', 'login_off', 'apps_menu', 'chatter', 'send', 'note', 'activity', 'import',
                'export', 'add_property', 'filter_button', 'custom_filter', 'custom_group')

_EMPTY = {'active': False, 'global': {}, 'menus': frozenset(), 'models': {}, 'fields': {}, 'domains': {},
          'elements': {}}


class AxsyncAccessEngine(models.AbstractModel):
    _name = 'axsync.access.engine'
    _description = 'AXSync Access Control Engine'

    # ------------------------------------------------------------------
    # Profile of the current user
    # ------------------------------------------------------------------
    @api.model
    def _user_group_ids(self, user):
        return set(user.groups_id.ids)

    @api.model
    def profile(self):
        """The merged restrictions of the current user for the current company."""
        if self.env.su:
            return _EMPTY
        return self._profile(self.env.uid, self.env.company.id)

    @api.model
    @tools.ormcache('uid', 'company_id')
    def _profile(self, uid, company_id):
        user = self.env['res.users'].sudo().browse(uid)
        if not user.exists() or uid == SUPERUSER_ID or user.has_group(MANAGER_GROUP):
            return _EMPTY
        groups = self._user_group_ids(user)
        rules = self.env['axsync.access.rule'].sudo().search([('active', '=', True)])
        rules = rules.filtered(
            lambda r: (user in r.user_ids or (set(r.group_ids.ids) & groups))
            and (not r.company_ids or company_id in r.company_ids.ids))
        if not rules:
            return _EMPTY
        glob = {
            'read_only': any(rules.mapped('read_only_user')), 'debug_off': any(rules.mapped('disable_debug')),
            'login_off': any(rules.mapped('disable_login')), 'apps_menu': any(rules.mapped('hide_apps_menu')),
            'chatter': any(rules.mapped('hide_chatter')), 'send': any(rules.mapped('hide_send_message')),
            'note': any(rules.mapped('hide_log_note')), 'activity': any(rules.mapped('hide_activity')),
            'import': any(rules.mapped('hide_import')), 'export': any(rules.mapped('hide_export')),
            'add_property': any(rules.mapped('hide_add_property')),
            'filter_button': any(rules.mapped('hide_filter_button')),
            'custom_filter': any(rules.mapped('hide_custom_filter')),
            'custom_group': any(rules.mapped('hide_custom_group')),
        }
        menus = set()
        for menu in rules.mapped('menu_ids'):
            menus.add(menu.id)
        models_ = {}
        for line in rules.mapped('model_line_ids'):
            m = models_.setdefault(line.model_name, {
                **{f: False for f in MODEL_FLAGS}, 'views': set(), 'reports': set(), 'actions': set()})
            for flag, fname in (('create', 'hide_create'), ('edit', 'hide_edit'), ('delete', 'hide_delete'),
                                ('archive', 'hide_archive'), ('duplicate', 'hide_duplicate'),
                                ('export', 'hide_export'), ('import', 'hide_import'),
                                ('add_property', 'hide_add_property'), ('read_only', 'read_only'),
                                ('chatter', 'hide_chatter'), ('send', 'hide_send_message'),
                                ('note', 'hide_log_note'), ('activity', 'hide_activity')):
                m[flag] = m[flag] or bool(line[fname])
            for vt in ('list', 'kanban', 'pivot', 'graph', 'calendar', 'activity', 'map'):
                if line['hide_view_' + vt]:
                    m['views'].add(vt)
            m['reports'].update(line.hide_report_ids.ids)
            m['actions'].update(line.hide_action_ids.ids)
            m['actions'].update(line.hide_window_action_ids.ids)
        for m in models_.values():
            m['views'] = frozenset(m['views'])
            m['reports'] = frozenset(m['reports'])
            m['actions'] = frozenset(m['actions'])
        fields_ = {}
        for line in rules.mapped('field_line_ids'):
            names = tuple(line.field_ids.mapped('name'))
            if not names:
                continue
            fields_.setdefault(line.model_name, []).append({
                'fields': names, 'invisible': line.invisible, 'readonly': line.readonly, 'required': line.required,
                'no_open': line.no_open, 'no_create': line.no_create, 'no_create_edit': line.no_create_edit,
                'kanban': line.hide_in_kanban, 'no_export': line.no_export, 'cond': line.condition_domain or '',
                'enforce': line.enforce_server})
        domains = {}
        for line in rules.mapped('domain_line_ids'):
            modes = {mode for mode, flag in (('read', line.apply_read), ('write', line.apply_write),
                                             ('create', line.apply_create), ('unlink', line.apply_unlink)) if flag}
            domains.setdefault(line.model_name, []).append({
                'domain': line.domain or '[]', 'modes': frozenset(modes),
                'hier': line.hierarchy_field_id.name if line.hierarchy else ''})
        elements = {}
        for line in rules.mapped('element_line_ids'):
            items = line.item_ids
            if not items:
                continue
            elements.setdefault(line.model_name, []).append({
                'kind': line.kind, 'names': frozenset(i.name for i in items if i.name),
                'labels': frozenset(i.label for i in items if i.label and not i.name),
                'cond': line.condition_domain or ''})
        return {'active': True, 'global': glob, 'menus': frozenset(menus), 'models': models_, 'fields': fields_,
                'domains': domains, 'elements': elements}

    @api.model
    def is_active(self):
        return self.profile()['active']

    @api.model
    def effective(self, prof, model):
        """Model flags merged with the global ones."""
        g = prof['global']
        m = prof['models'].get(model) or {}
        eff = {f: bool(m.get(f)) for f in MODEL_FLAGS}
        for f in ('read_only', 'chatter', 'send', 'note', 'activity', 'import', 'export', 'add_property'):
            eff[f] = eff[f] or bool(g.get(f))
        eff['views'] = m.get('views', frozenset())
        eff['reports'] = m.get('reports', frozenset())
        eff['actions'] = m.get('actions', frozenset())
        return eff

    @api.model
    def hidden_menu_ids(self):
        prof = self.profile()
        if not prof['menus']:
            return set()
        hidden = set()
        Menu = self.env['ir.ui.menu'].sudo().with_context(**{'ir.ui.menu.full_list': True, 'active_test': False})
        for menu in Menu.browse(list(prof['menus'])).exists():
            hidden.update(Menu.search([('id', 'child_of', menu.id)]).ids)
        return hidden

    @api.model
    def session_flags(self):
        """What the web client needs to know to hide buttons that are not part of a view."""
        prof = self.profile()
        if not prof['active']:
            return {}
        models_ = {}
        for model, m in prof['models'].items():
            eff = self.effective(prof, model)
            flags = {k: True for k in ('archive', 'duplicate', 'delete', 'export', 'add_property', 'create')
                     if eff[k] or (eff['read_only'] and k in ('delete', 'create', 'duplicate', 'archive'))}
            if flags:
                models_[model] = flags
        g = prof['global']
        return {
            'global': {k: True for k, v in g.items() if v and k in (
                'read_only', 'apps_menu', 'export', 'add_property', 'filter_button', 'custom_filter',
                'custom_group', 'send', 'note', 'activity', 'chatter')},
            'models': models_,
        }

    # ------------------------------------------------------------------
    # Domains
    # ------------------------------------------------------------------
    @api.model
    def _eval_context(self, user=None):
        user = (user or self.env.user).sudo()
        return {
            'user': user, 'uid': user.id, 'time': safe_time, 'datetime': safe_datetime, 'relativedelta': relativedelta,
            'company_id': self.env.company.id, 'company_ids': self.env.companies.ids,
            'context_today': lambda: fields.Date.context_today(self),
        }

    @api.model
    def eval_domain(self, domain_str, user=None):
        domain = safe_eval(domain_str or '[]', self._eval_context(user))
        if not isinstance(domain, (list, tuple)):
            raise ValueError(_('A domain must be a list.'))
        return expression.normalize_domain(list(domain))

    @api.model
    def subordinate_ids(self, uid):
        """The user and everyone who reports to them, directly or not."""
        seen = {uid}
        frontier = [uid]
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        while frontier:
            children = Users.search([('axsync_manager_id', 'in', frontier)]).ids
            frontier = [c for c in children if c not in seen]
            seen.update(frontier)
        return list(seen)

    @api.model
    def extra_domain(self, model, mode):
        """Domain added to the security domain of the current user for this model and operation."""
        prof = self.profile()
        if not prof['active']:
            return []
        parts = []
        for line in prof['domains'].get(model, ()):
            if mode not in line['modes']:
                continue
            dom = self.eval_domain(line['domain'])
            if line['hier']:
                dom = expression.AND([dom, [(line['hier'], 'in', self.subordinate_ids(self.env.uid))]])
            if dom:
                parts.append(dom)
        return expression.AND(parts) if parts else []

    @api.model
    def is_blocked(self, model, mode):
        """True when the current user may not perform the operation on the model."""
        if mode == 'read' or self.env.su:
            return False
        prof = self.profile()
        if not prof['active']:
            return False
        try:
            if self.env[model]._transient:
                return False
        except KeyError:
            return False
        eff = self.effective(prof, model)
        if eff['read_only'] and model not in READ_ONLY_EXEMPT:
            return True
        return {'create': eff['create'], 'write': eff['edit'], 'unlink': eff['delete']}.get(mode, False)

    @api.model
    def blocked_message(self, model, mode):
        label = {'create': _('create'), 'write': _('edit'), 'unlink': _('delete')}.get(mode, mode)
        return _('Your access rights do not allow you to %(op)s records of "%(model)s". '
                 'Contact your administrator if you need this access.',
                 op=label, model=self.env['ir.model']._get(model).name or model)

    # ------------------------------------------------------------------
    # Conditions: domain -> client side expression
    # ------------------------------------------------------------------
    @api.model
    def domain_to_expression(self, domain_str, ctx=None):
        domain = expression.normalize_domain(safe_eval(domain_str or '[]', {
            'uid': (ctx or {}).get('uid', 0), 'time': safe_time, 'datetime': safe_datetime, 'relativedelta': relativedelta}))
        if not domain:
            return ''
        stack = list(domain)

        def leaf(term):
            field, op, val = term
            if not isinstance(field, str) or '.' in field:
                raise ValueError(_('Only simple fields of the same model are supported (%s).', field))
            if op in ('=', '!='):
                if val is False or val is None:
                    return ('not %s' if op == '=' else '%s') % field
                if val is True:
                    return ('%s' if op == '=' else 'not %s') % field
                return '%s %s %r' % (field, '==' if op == '=' else '!=', val)
            if op in ('in', 'not in'):
                if not isinstance(val, (list, tuple)):
                    raise ValueError(_('The value of "%s" must be a list.', op))
                if any(isinstance(v, (datetime.date, datetime.datetime)) for v in val):
                    raise ValueError(_('Dates are not supported in conditions.'))
                return '%s %s %r' % (field, op, list(val))
            if op in ('<', '>', '<=', '>='):
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(_('Comparisons support numbers only.'))
                return '%s %s %r' % (field, op, val)
            raise ValueError(_('The operator "%s" is not supported in conditions.', op))

        def build():
            tok = stack.pop(0)
            if tok == '&':
                a = build()
                b = build()
                return '(%s and %s)' % (a, b)
            if tok == '|':
                a = build()
                b = build()
                return '(%s or %s)' % (a, b)
            if tok == '!':
                return 'not (%s)' % build()
            return '(%s)' % leaf(tok)
        return build()

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------
    @api.model
    def _walk(self, node):
        for child in node:
            if not isinstance(child.tag, str):
                continue
            if node.tag == 'field' and child.tag in VIEW_TAGS:
                yield 'sub', node, child
                continue
            yield 'el', node, child
            yield from self._walk(child)

    @api.model
    def _merge_attr(self, node, attr, expr):
        """Combine an existing modifier expression with a new one using 'or'."""
        old = (node.get(attr) or '').strip()
        if expr in ('1', 'True'):
            node.set(attr, '1')
        elif old in ('1', 'True'):
            return
        elif old and old not in ('0', 'False'):
            node.set(attr, '(%s) or (%s)' % (old, expr))
        else:
            node.set(attr, expr)

    @api.model
    def _set_options(self, node, extra):
        old = (node.get('options') or '').strip()
        body = ', '.join("'%s': True" % k for k in extra)
        if old.startswith('{') and old.rstrip() != '{}':
            node.set('options', '{%s, %s' % (body, old[1:]))
        else:
            node.set('options', '{%s}' % body)

    @api.model
    def _comodel(self, model, fname):
        field = self.env[model]._fields.get(fname) if model in self.env else None
        return field.comodel_name if field is not None and field.relational else None

    @api.model
    def _hide_node(self, node, cond, remove_ok=False):
        if cond:
            self._merge_attr(node, 'invisible', cond)
        elif remove_ok and node.getparent() is not None:
            parent = node.getparent()
            tail = node.tail
            prev = node.getprevious()
            if tail and tail.strip() == '':
                tail = None
            if tail:
                if prev is not None:
                    prev.tail = (prev.tail or '') + tail
                else:
                    parent.text = (parent.text or '') + tail
            parent.remove(node)
        else:
            node.set('invisible', '1')

    @api.model
    def _apply_root(self, root, eff):
        tag = root.tag
        if tag in ('form', 'tree', 'list', 'kanban'):
            if eff['read_only'] or eff['create']:
                root.set('create', 'false')
            if eff['read_only'] or eff['edit']:
                root.set('edit', 'false')
            if eff['read_only'] or eff['delete']:
                root.set('delete', 'false')
            if eff['read_only'] or eff['duplicate']:
                root.set('duplicate', 'false')
        if tag in LIST_TAGS + ('kanban',):
            if eff['import']:
                root.set('import', 'false')
            if eff['export']:
                root.set('export_xlsx', 'false')
        if tag == 'kanban' and (eff['archive'] or eff['read_only']):
            root.set('archivable', 'false')
        if tag == 'form':
            nodes = list(root.iter('chatter')) + root.xpath(
                ".//div[contains(concat(' ', normalize-space(@class), ' '), ' oe_chatter ')]")
            if eff['chatter']:
                for node in nodes:
                    self._hide_node(node, '', remove_ok=True)
            else:
                classes = (root.get('class') or '').split()
                for flag, cls in (('send', 'axsync-no-send'), ('note', 'axsync-no-note'),
                                  ('activity', 'axsync-no-activity')):
                    if eff[flag] and cls not in classes:
                        classes.append(cls)
                if classes:
                    root.set('class', ' '.join(classes))

    @api.model
    def _apply_view(self, root, model, prof):
        eff = self.effective(prof, model)
        self._apply_root(root, eff)
        flines = prof['fields'].get(model, ())
        elines = prof['elements'].get(model, ())
        if not flines and not elines:
            for kind, parent, child in list(self._walk(root)):
                if kind == 'sub':
                    comodel = self._comodel(model, parent.get('name'))
                    if comodel:
                        self._apply_view(child, comodel, prof)
            return
        Model = self.env[model]
        for kind, parent, child in list(self._walk(root)):
            if kind == 'sub':
                comodel = self._comodel(model, parent.get('name'))
                if comodel:
                    self._apply_view(child, comodel, prof)
                continue
            tag = child.tag
            if tag == 'field':
                fname = child.get('name')
                for line in flines:
                    if fname in line['fields']:
                        self._apply_field(child, parent, root, Model, line)
                if root.tag == 'search':
                    continue
            elif tag == 'label' and child.get('for'):
                for line in flines:
                    if child.get('for') in line['fields'] and line['invisible']:
                        self._hide_node(child, self._cond(line['cond']))
            if elines:
                self._apply_elements(child, root, elines)
        # group-by options of hidden fields
        if root.tag == 'search':
            for line in flines:
                if line['invisible'] and not line['cond']:
                    for node in list(root.iter('filter')):
                        ctx = node.get('context') or ''
                        if 'group_by' in ctx and any(("'%s'" % f in ctx or '"%s"' % f in ctx
                                                      or ("'%s:" % f) in ctx) for f in line['fields']):
                            self._hide_node(node, '', remove_ok=True)

    @api.model
    def _cond(self, cond):
        return self.domain_to_expression(cond, {'uid': self.env.uid}) if cond else ''

    @api.model
    def _apply_field(self, node, parent, root, Model, line):
        fname = node.get('name')
        cond = self._cond(line['cond'])
        rtag = root.tag
        if rtag == 'search':
            if line['invisible'] and not cond:
                self._hide_node(node, '', remove_ok=True)
            return
        if rtag in ('pivot', 'graph'):
            if line['invisible'] and not cond:
                self._hide_node(node, '', remove_ok=True)
            return
        if rtag in ('calendar', 'gantt', 'map', 'activity', 'cohort'):
            return
        if line['invisible']:
            if cond:
                self._merge_attr(node, 'invisible', cond)
            elif rtag in LIST_TAGS and parent is root:
                node.set('column_invisible', '1')
            else:
                node.set('invisible', '1')
        elif line['kanban'] and rtag == 'kanban':
            node.set('invisible', '1')
        if line['readonly'] and rtag != 'kanban':
            self._merge_attr(node, 'readonly', cond or '1')
        if line['required'] and rtag != 'kanban' and not line['invisible']:
            self._merge_attr(node, 'required', cond or '1')
        field = Model._fields.get(fname)
        if field is not None and field.type in ('many2one', 'many2many', 'one2many'):
            opts = [k for k, f in (('no_open', 'no_open'), ('no_create', 'no_create'),
                                   ('no_quick_create', 'no_create'),
                                   ('no_create_edit', 'no_create_edit')) if line[f]]
            if opts and field.type != 'one2many':
                self._set_options(node, opts)

    @api.model
    def _apply_elements(self, node, root, elines):
        tag = node.tag
        name = node.get('name') or ''
        label = (node.get('string') or ''.join(node.itertext())).strip()[:120]
        for line in elines:
            kind = line['kind']
            if kind == 'button':
                if not (tag == 'button' or (tag == 'a' and node.get('type') in ('object', 'action'))):
                    continue
            elif kind == 'tab':
                if tag != 'page':
                    continue
            elif tag != 'filter' or root.tag != 'search':
                continue
            else:
                is_group = 'group_by' in (node.get('context') or '')
                if (kind == 'group_by') != is_group:
                    continue
            if not ((name and name in line['names']) or (not name and label in line['labels'])):
                continue
            cond = self._cond(line['cond']) if kind in ('button', 'tab') else ''
            self._hide_node(node, cond, remove_ok=(tag in ('a', 'filter')))

    @api.model
    def postprocess_view(self, model, result):
        if self.env.su:
            return result
        prof = self.profile()
        if not prof['active'] or not result.get('arch'):
            return result
        try:
            root = etree.fromstring(result['arch'].encode())
        except etree.XMLSyntaxError:
            return result
        self._apply_view(root, model, prof)
        result = dict(result)
        result['arch'] = etree.tostring(root, encoding='unicode')
        return result

    # ------------------------------------------------------------------
    # Records
    # ------------------------------------------------------------------
    @api.model
    def hidden_fields(self, model, strict=True):
        prof = self.profile()
        names = set()
        for line in prof['fields'].get(model, ()):
            if line['invisible'] and not line['cond']:
                names.update(line['fields'])
        return names

    @api.model
    def blank_hidden(self, model, records):
        if not records or self.env.su:
            return records
        names = self.hidden_fields(model)
        if not names:
            return records
        fields_ = self.env[model]._fields
        for rec in records:
            for name in names:
                if name in rec:
                    rec[name] = [] if fields_[name].type in ('one2many', 'many2many') else False
        return records

    @api.model
    def check_write(self, model, vals, records=None, creating=False):
        if self.env.su:
            return
        prof = self.profile()
        if not prof['active']:
            return
        eff = self.effective(prof, model)
        if not creating and 'active' in vals and (eff['archive'] or eff['read_only']):
            raise AccessError(_('You are not allowed to archive or unarchive records of "%s".',
                                self.env['ir.model']._get(model).name or model))
        if creating:
            return
        for line in prof['fields'].get(model, ()):
            if line['readonly'] and line['enforce'] and not line['cond']:
                bad = [f for f in line['fields'] if f in vals]
                if bad:
                    raise AccessError(_('You are not allowed to change: %s.', ', '.join(
                        self.env[model]._fields[f]._description_string(self.env) for f in bad)))

    @api.model
    def check_required(self, records, vals=None, creating=False):
        if self.env.su or not records:
            return
        prof = self.profile()
        if not prof['active']:
            return
        model = records._name
        for line in prof['fields'].get(model, ()):
            if not (line['required'] and line['enforce'] and not line['cond']):
                continue
            for fname in line['fields']:
                if not creating and vals is not None and fname not in vals:
                    continue
                field = records._fields[fname]
                if field.type == 'boolean':
                    continue
                for rec in records:
                    value = rec[fname]
                    if value is None or value is False or value == '' or (field.relational and not value):
                        raise ValidationError(_('The field "%(field)s" is required.',
                                                field=field._description_string(self.env)))

    @api.model
    def check_export(self, model, paths):
        if self.env.su:
            return
        prof = self.profile()
        if not prof['active']:
            return
        eff = self.effective(prof, model)
        if eff['export']:
            raise AccessError(_('Export is not allowed for you on "%s".', self.env['ir.model']._get(model).name or model))
        blocked = set()
        for line in prof['fields'].get(model, ()):
            if line['no_export'] or (line['invisible'] and not line['cond']):
                blocked.update(line['fields'])
        for path in paths or ():
            first = (path if isinstance(path, str) else '/'.join(path)).split('/')[0].split('.')[0]
            if first in blocked:
                raise AccessError(_('The field "%s" cannot be exported.', first))

    @api.model
    def check_import(self, model):
        if self.env.su:
            return
        prof = self.profile()
        if prof['active'] and self.effective(prof, model)['import']:
            raise AccessError(_('Import is not allowed for you on "%s".', self.env['ir.model']._get(model).name or model))

    @api.model
    def check_duplicate(self, model):
        if self.env.su:
            return
        prof = self.profile()
        if prof['active']:
            eff = self.effective(prof, model)
            if eff['duplicate'] or eff['read_only']:
                raise AccessError(_('Duplicating records of "%s" is not allowed for you.',
                                    self.env['ir.model']._get(model).name or model))

    @api.model
    def chatter_blocked(self, model, kind):
        """kind is 'send', 'note' or 'activity'."""
        if self.env.su:
            return False
        prof = self.profile()
        if not prof['active']:
            return False
        eff = self.effective(prof, model)
        return eff['chatter'] or eff[kind]
