# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from lxml import etree

from odoo.exceptions import AccessDenied, AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

TREE = 'list'


@tagged('post_install', '-at_install', 'axsync_acc')
class TestUserAccessControl(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env['axsync.access.rule']
        cls.engine = cls.env['axsync.access.engine']
        group_ids = [cls.env.ref('base.group_user').id, cls.env.ref('base.group_partner_manager').id,
                     cls.env.ref('base.group_allow_export').id]
        cls.user_a = cls.env['res.users'].create({
            'name': 'Restricted User', 'login': 'axsync_a', 'email': 'a@example.com', 'password': 'axsync_pw_a', 'groups_id': [(6, 0, group_ids)]})
        cls.user_b = cls.env['res.users'].create({
            'name': 'Free User', 'login': 'axsync_b', 'email': 'b@example.com', 'password': 'axsync_pw_b', 'groups_id': [(6, 0, group_ids)]})
        cls.partner = cls.env['res.partner'].create({'name': 'Acme Test Partner', 'phone': '555-1234', 'email': 'a@x.com'})
        cls.other = cls.env['res.partner'].create({'name': 'Zeta Other Partner', 'phone': '555-9999'})
        cls.m_partner = cls.env['ir.model']._get('res.partner')
        cls.rule = cls.Rule.create({'name': 'Test rule', 'user_ids': [(6, 0, cls.user_a.ids)]})

    # helpers
    def _model_line(self, **vals):
        vals.update({'rule_id': self.rule.id, 'model_id': self.m_partner.id})
        return self.env['axsync.access.model.line'].create(vals)

    def _field_line(self, names, **vals):
        fields_ = self.env['ir.model.fields'].search([('model_id', '=', self.m_partner.id), ('name', 'in', names)])
        vals.update({'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'field_ids': [(6, 0, fields_.ids)]})
        return self.env['axsync.access.field.line'].create(vals)

    def _view(self, user, vtype='form'):
        res = self.env['res.partner'].with_user(user).get_view(None, vtype)
        return etree.fromstring(res['arch'].encode())

    def _field_node(self, root, name):
        nodes = root.xpath("//field[@name='%s']" % name)
        return nodes[0] if nodes else None

    # ------------------------------------------------------------------
    def test_01_rule_needs_target(self):
        with self.assertRaises(ValidationError):
            self.Rule.create({'name': 'No target'})

    def test_02_menu_hidden(self):
        menu = self.env.ref('mail.menu_root_discuss')
        Menu = self.env['ir.ui.menu']
        self.assertIn(menu.id, Menu.with_user(self.user_a)._visible_menu_ids(False))
        self.rule.menu_ids = [(6, 0, menu.ids)]
        self.assertNotIn(menu.id, Menu.with_user(self.user_a)._visible_menu_ids(False))
        self.assertIn(menu.id, Menu.with_user(self.user_b)._visible_menu_ids(False))

    def test_03_model_create_edit_delete(self):
        Partner = self.env['res.partner']
        line = self._model_line(hide_create=True)
        with self.assertRaises(AccessError):
            Partner.with_user(self.user_a).create({'name': 'Blocked'})
        self.assertTrue(Partner.with_user(self.user_b).create({'name': 'Allowed'}))
        line.write({'hide_create': False, 'hide_edit': True})
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).write({'name': 'Changed'})
        line.write({'hide_edit': False, 'hide_delete': True})
        with self.assertRaises(AccessError):
            self.other.with_user(self.user_a).unlink()
        self.assertFalse(Partner.with_user(self.user_a).has_access('unlink'))

    def test_04_read_only_user(self):
        self.rule.read_only_user = True
        Partner = self.env['res.partner'].with_user(self.user_a)
        self.assertTrue(Partner.search([('id', '=', self.partner.id)]))
        for op in (lambda: Partner.create({'name': 'x'}), lambda: self.partner.with_user(self.user_a).write({'name': 'y'}),
                   lambda: self.other.with_user(self.user_a).unlink()):
            with self.assertRaises(AccessError):
                op()
        # session bookkeeping must still work
        self.env['res.users.log'].with_user(self.user_a).sudo().create({})
        self.assertFalse(self.engine.with_user(self.user_a).is_blocked('res.users.log', 'create'))
        # the free user is not touched
        self.assertTrue(self.env['res.partner'].with_user(self.user_b).create({'name': 'ok'}))

    def test_05_domain_read(self):
        self.env['axsync.access.domain.line'].create({
            'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'domain': "[('name', 'ilike', 'Acme')]"})
        found = self.env['res.partner'].with_user(self.user_a).search([('id', 'in', (self.partner | self.other).ids)])
        self.assertEqual(found, self.partner)
        found_b = self.env['res.partner'].with_user(self.user_b).search([('id', 'in', (self.partner | self.other).ids)])
        self.assertEqual(found_b, self.partner | self.other)

    def test_06_domain_soft_write_only(self):
        self.env['axsync.access.domain.line'].create({
            'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'domain': "[('name', 'ilike', 'Acme')]",
            'apply_read': False, 'apply_create': False, 'apply_unlink': False})
        Partner = self.env['res.partner'].with_user(self.user_a)
        self.assertEqual(Partner.search([('id', 'in', (self.partner | self.other).ids)]), self.partner | self.other)
        self.partner.with_user(self.user_a).write({'comment': 'ok'})
        with self.assertRaises(AccessError):
            self.other.with_user(self.user_a).write({'comment': 'nope'})

    def test_07_domain_user_context(self):
        self.env['axsync.access.domain.line'].create({
            'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'domain': "[('create_uid', '=', user.id)]"})
        mine = self.env['res.partner'].with_user(self.user_a).create({'name': 'Mine'}) if False else None
        found = self.env['res.partner'].with_user(self.user_a).search([('id', '=', self.partner.id)])
        self.assertFalse(found)
        self.assertEqual(self.env['res.partner'].with_user(self.user_b).search([('id', '=', self.partner.id)]),
                         self.partner)

    def test_08_hierarchy(self):
        boss, junior = self.user_a, self.user_b
        junior.axsync_manager_id = boss
        self.assertEqual(set(self.engine.subordinate_ids(boss.id)), {boss.id, junior.id})
        field = self.env['ir.model.fields']._get('res.partner', 'user_id')
        self.env['axsync.access.domain.line'].create({
            'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'domain': '[]', 'hierarchy': True,
            'hierarchy_field_id': field.id})
        self.partner.user_id = junior
        self.other.user_id = self.env.ref('base.user_admin')
        found = self.env['res.partner'].with_user(boss).search([('id', 'in', (self.partner | self.other).ids)])
        self.assertEqual(found, self.partner)
        with self.assertRaises(ValidationError):
            self.env['axsync.access.domain.line'].create({
                'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'hierarchy': True})

    def test_09_company_scope(self):
        company2 = self.env['res.company'].create({'name': 'Second Test Company'})
        self.rule.company_ids = [(6, 0, company2.ids)]
        self._model_line(hide_create=True)
        # the user works in the main company: the rule does not apply
        self.assertTrue(self.env['res.partner'].with_user(self.user_a).create({'name': 'Still fine'}))
        self.user_a.write({'company_ids': [(4, company2.id)], 'company_id': company2.id})
        with self.assertRaises(AccessError):
            self.env['res.partner'].with_user(self.user_a).with_company(company2).create({'name': 'Blocked'})

    def test_10_group_rule(self):
        self.rule.write({'user_ids': [(5, 0, 0)], 'group_ids': [(6, 0, self.env.ref('base.group_partner_manager').ids)]})
        self._model_line(hide_create=True)
        with self.assertRaises(AccessError):
            self.env['res.partner'].with_user(self.user_a).create({'name': 'Group blocked'})
        with self.assertRaises(AccessError):
            self.env['res.partner'].with_user(self.user_b).create({'name': 'Group blocked'})

    def test_11_manager_never_restricted(self):
        manager = self.env['res.users'].create({
            'name': 'AC Manager', 'login': 'axsync_mgr', 'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id,
                self.env.ref('axsync_user_access_control.group_axsync_access_manager').id])]})
        self.rule.user_ids = [(4, manager.id)]
        self.rule.read_only_user = True
        self.assertTrue(self.env['res.partner'].with_user(manager).create({'name': 'Manager creates'}))
        self.assertTrue(self.env.ref('base.user_admin').has_group('axsync_user_access_control.group_axsync_access_manager'))

    def test_12_view_root_attributes(self):
        self._model_line(hide_create=True, hide_edit=True, hide_delete=True, hide_duplicate=True, hide_import=True,
                         hide_export=True)
        form = self._view(self.user_a)
        for attr in ('create', 'edit', 'delete', 'duplicate'):
            self.assertEqual(form.get(attr), 'false', attr)
        tree = self._view(self.user_a, TREE)
        self.assertEqual(tree.get('import'), 'false')
        self.assertEqual(tree.get('export_xlsx'), 'false')
        free = self._view(self.user_b)
        self.assertIsNone(free.get('create'))

    def test_13_field_invisible_readonly_required(self):
        self._field_line(['phone'], invisible=True)
        self._field_line(['email'], readonly=True)
        self._field_line(['function'], required=True)
        root = self._view(self.user_a)
        self.assertEqual(self._field_node(root, 'phone').get('invisible'), '1')
        self.assertEqual(self._field_node(root, 'email').get('readonly'), '1')
        self.assertEqual(self._field_node(root, 'function').get('required'), '1')
        tree = self._view(self.user_a, TREE)
        node = self._field_node(tree, 'phone')
        if node is not None:
            self.assertEqual(node.get('column_invisible'), '1')
        free = self._view(self.user_b)
        self.assertNotEqual(self._field_node(free, 'phone').get('invisible'), '1')

    def test_14_hidden_field_is_blank_on_read(self):
        self._field_line(['phone'], invisible=True)
        data = self.partner.with_user(self.user_a).read(['name', 'phone'])[0]
        self.assertEqual(data['name'], 'Acme Test Partner')
        self.assertFalse(data['phone'])
        self.assertEqual(self.partner.with_user(self.user_b).read(['phone'])[0]['phone'], '555-1234')
        # the same for the web client entry point
        web = self.partner.with_user(self.user_a).web_read({'name': {}, 'phone': {}})[0]
        self.assertFalse(web['phone'])

    def test_15_condition(self):
        self._field_line(['email'], readonly=True, condition_domain="[('name', '=', 'Acme Test Partner')]")
        node = self._field_node(self._view(self.user_a), 'email')
        self.assertEqual(node.get('readonly'), "(name == 'Acme Test Partner')")
        self.assertEqual(self.engine.domain_to_expression("[('a', '=', 1), '|', ('b', '!=', False), ('c', 'in', ['x', 'y'])]"),
                         "((a == 1) and ((b) or (c in ['x', 'y'])))")
        self.assertEqual(self.engine.domain_to_expression("[('a', '=', False)]"), '(not a)')
        with self.assertRaises(ValueError):
            self.engine.domain_to_expression("[('partner_id.name', '=', 'x')]")
        with self.assertRaises(ValidationError):
            self._field_line(['email'], readonly=True, condition_domain="[('name', 'ilike', 'x')]")

    def test_16_enforce_server(self):
        self._field_line(['email'], readonly=True, enforce_server=True)
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).write({'email': 'new@x.com'})
        self.partner.with_user(self.user_a).write({'comment': 'fine'})
        self.partner.with_user(self.user_b).write({'email': 'new@x.com'})
        self._field_line(['function'], required=True, enforce_server=True)
        with self.assertRaises(ValidationError):
            self.partner.with_user(self.user_a).write({'function': False})

    def test_17_relational_options(self):
        self._field_line(['country_id'], no_open=True, no_create=True, no_create_edit=True)
        node = self._field_node(self._view(self.user_a), 'country_id')
        options = node.get('options')
        for key in ('no_open', 'no_create', 'no_quick_create', 'no_create_edit'):
            self.assertIn("'%s': True" % key, options)

    def test_18_elements(self):
        items = self.env['axsync.access.item'].scan_model('res.partner')
        kinds = set(items.mapped('kind'))
        self.assertIn('tab', kinds)
        self.assertIn('filter', kinds)
        self.assertIn('group_by', kinds)
        form = self._view(self.user_b)
        page = form.xpath('//page')[0]
        item = items.filtered(lambda i: i.kind == 'tab' and (i.name == page.get('name') or i.label == page.get('string')))[:1]
        self.assertTrue(item)
        self.env['axsync.access.element.line'].create({
            'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'kind': 'tab', 'item_ids': [(6, 0, item.ids)]})
        hidden_form = self._view(self.user_a)
        hidden_pages = [p for p in hidden_form.xpath('//page') if p.get('invisible') == '1']
        self.assertTrue(hidden_pages)
        search_items = items.filtered(lambda i: i.kind == 'filter')[:1]
        self.env['axsync.access.element.line'].create({
            'rule_id': self.rule.id, 'model_id': self.m_partner.id, 'kind': 'filter',
            'item_ids': [(6, 0, search_items.ids)]})
        search = self._view(self.user_a, 'search')
        self.assertFalse(search.xpath("//filter[@name='%s']" % search_items.name))

    def test_19_chatter(self):
        self._model_line(hide_send_message=True, hide_log_note=True)
        form = self._view(self.user_a)
        classes = (form.get('class') or '').split()
        self.assertIn('axsync-no-send', classes)
        self.assertIn('axsync-no-note', classes)
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).message_post(body='hello', message_type='comment',
                                                              subtype_xmlid='mail.mt_comment')
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).message_post(body='note', message_type='comment',
                                                              subtype_xmlid='mail.mt_note')
        self.assertTrue(self.partner.with_user(self.user_b).message_post(body='free', message_type='comment',
                                                                          subtype_xmlid='mail.mt_comment'))
        # tracking and system notifications are not blocked
        self.partner.with_user(self.user_a).message_post(body='system', message_type='notification')
        self.rule.model_line_ids.hide_chatter = True
        hidden = self._view(self.user_a)
        self.assertFalse(hidden.xpath("//*[contains(@class, 'oe_chatter')]") or hidden.xpath('//chatter'))

    def test_20_activity_blocked(self):
        self._model_line(hide_activity=True)
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).activity_schedule('mail.mail_activity_data_todo', summary='x')
        self.assertTrue(self.partner.with_user(self.user_b).activity_schedule('mail.mail_activity_data_todo', summary='x'))

    def test_21_hide_view_types(self):
        action = self.env.ref('base.action_partner_form')
        self._model_line(hide_view_kanban=True)
        vals = action.with_user(self.user_a).sudo()._get_action_dict()
        self.assertNotIn('kanban', [v[1] for v in vals['views']])
        self.assertNotIn('kanban', vals['view_mode'])
        vals_b = action.with_user(self.user_b).sudo()._get_action_dict()
        self.assertIn('kanban', [v[1] for v in vals_b['views']])

    def test_22_hide_actions_in_bindings(self):
        server = self.env['ir.actions.server'].create({
            'name': 'Axsync Test Action', 'model_id': self.m_partner.id, 'state': 'code', 'code': 'pass',
            'binding_model_id': self.m_partner.id})
        Actions = self.env['ir.actions.actions']
        ids = [a['id'] for a in Actions.with_user(self.user_a).get_bindings('res.partner').get('action', [])]
        self.assertIn(server.id, ids)
        self._model_line(hide_action_ids=[(6, 0, server.ids)])
        ids = [a['id'] for a in Actions.with_user(self.user_a).get_bindings('res.partner').get('action', [])]
        self.assertNotIn(server.id, ids)
        ids_b = [a['id'] for a in Actions.with_user(self.user_b).get_bindings('res.partner').get('action', [])]
        self.assertIn(server.id, ids_b)

    def test_23_duplicate_archive_export_import(self):
        line = self._model_line(hide_duplicate=True, hide_archive=True, hide_export=True, hide_import=True)
        Partner = self.env['res.partner'].with_user(self.user_a)
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).copy()
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).write({'active': False})
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).export_data(['name'])
        with self.assertRaises(AccessError):
            Partner.load(['name'], [['Imported']])
        self.assertTrue(self.partner.with_user(self.user_b).copy())
        self.assertEqual(self.partner.with_user(self.user_b).export_data(['name'])['datas'][0][0], 'Acme Test Partner')
        line.unlink()

    def test_24_field_not_exportable(self):
        self._field_line(['phone'], no_export=True)
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user_a).export_data(['name', 'phone'])
        self.assertTrue(self.partner.with_user(self.user_a).export_data(['name']))

    def test_25_global_export_group(self):
        self.user_a.groups_id = [(4, self.env.ref('base.group_allow_export').id)]
        self.assertTrue(self.user_a.has_group('base.group_allow_export'))
        self.rule.hide_export = True
        self.assertFalse(self.env['res.users'].with_user(self.user_a).browse(self.user_a.id).has_group('base.group_allow_export'))
        self.assertTrue(self.env['res.users'].with_user(self.user_b).browse(self.user_b.id).has_group('base.group_user'))

    def test_26_login_disabled(self):
        user = self.user_a
        user.with_user(user)._check_credentials({'type': 'password', 'password': 'axsync_pw_a'}, {'interactive': True})
        self.rule.disable_login = True
        with self.assertRaises(AccessDenied):
            user.with_user(user)._check_credentials({'type': 'password', 'password': 'axsync_pw_a'}, {'interactive': True})
        self.assertTrue(user._axsync_login_disabled())
        self.assertFalse(self.user_b._axsync_login_disabled())

    def test_27_session_flags(self):
        self.rule.write({'hide_custom_group': True, 'hide_apps_menu': True})
        self._model_line(hide_archive=True, hide_duplicate=True)
        flags = self.engine.with_user(self.user_a).session_flags()
        self.assertTrue(flags['global']['custom_group'])
        self.assertTrue(flags['global']['apps_menu'])
        self.assertTrue(flags['models']['res.partner']['archive'])
        self.assertTrue(flags['models']['res.partner']['duplicate'])
        self.assertFalse(self.engine.with_user(self.user_b).session_flags())

    def test_28_inactive_rule(self):
        self._model_line(hide_create=True)
        self.rule.active = False
        self.assertTrue(self.env['res.partner'].with_user(self.user_a).create({'name': 'No rule now'}))

    def test_29_report_hidden(self):
        report = self.env['ir.actions.report'].search([('model', '=', 'res.partner')], limit=1)
        if not report:
            self.skipTest('no partner report available')
        self._model_line(hide_report_ids=[(6, 0, report.ids)])
        with self.assertRaises(AccessError):
            self.env['ir.actions.report'].with_user(self.user_a)._render_qweb_pdf(report.report_name, self.partner.ids)

    def test_30_subviews_follow_comodel(self):
        line = self.env['axsync.access.model.line'].create({
            'rule_id': self.rule.id, 'model_id': self.env['ir.model']._get('res.partner').id, 'hide_create': True})
        root = self._view(self.user_a)
        child_views = root.xpath("//field[@name='child_ids']/*[self::form or self::kanban or self::list]")
        self.assertTrue(child_views)
        self.assertEqual(root.get('create'), 'false')
        for view in child_views:
            if view.tag in ('kanban', 'list', 'form'):
                self.assertEqual(view.get('create'), 'false')
        line.unlink()
