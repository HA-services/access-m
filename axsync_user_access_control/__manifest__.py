# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
{
    'name': 'User Access Control',
    'summary': 'Hide menus, fields, buttons, tabs and records per user. Read-only users, dev mode and login control',
    'description': 'AXSync User Access Control. Restrict what each user or group can see and do in Odoo: menus, '
                   'models, fields, records, buttons, tabs, filters, chatter, reports and more, without code.',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'author': 'AXSync',
    'website': 'https://www.axsync.com',
    'support': 'hunain@axsync.com',
    'license': 'OPL-1',
    'price': 85.0,
    'currency': 'USD',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/axsync_access_groups.xml',
        'security/ir.model.access.csv',
        'views/access_rule_views.xml',
        'views/res_users_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'axsync_user_access_control/static/src/js/access_control.js',
            'axsync_user_access_control/static/src/css/access_control.css',
        ],
    },
    'images': [
        'static/description/axsync_banner.png',
        'static/description/axsync_dashboard_screenshot.png',
        'static/description/axsync_screenshot_1.png',
        'static/description/axsync_screenshot_2.png',
        'static/description/axsync_screenshot_3.png',
        'static/description/axsync_screenshot_4.png',
        'static/description/axsync_screenshot_5.png',
        'static/description/axsync_screenshot_6.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
