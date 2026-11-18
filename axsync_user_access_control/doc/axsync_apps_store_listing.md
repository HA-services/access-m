# Odoo Apps Store listing: copy-ready text (20.0)

## Product title
User Access Control
(Manifest name, 19 characters, the Apps Store limit is 25. Marketing name used on the description page: AXSync User Access Control.)

## Short description (summary)
Hide menus, fields, buttons, tabs and records per user or group. Read-only users, developer mode and login control.

## Full product description
AXSync User Access Control lets an administrator decide what each user or group sees and does in Odoo, without code. Create a rule, choose the users or groups, and tick what to hide or block: menus, fields, buttons, tabs, filters, chatter, reports, view types, create, edit, delete, archive, duplicate, export and import. Limit records with a domain, make users read-only, switch off developer mode or disable a login.

Problem it solves: standard access rights are coarse. Hiding one field or one button for one team usually means a developer and a custom view, and exports and deletes cannot be limited per user.

Who should use it: Odoo administrators, consultants and company owners who need finer access than the standard groups give, including auditors, trainees, sales teams and outsourced staff.

How it works: open Access Control > Rules, choose the users or groups, then use the tabs Menus, Models, Fields, Records, Buttons Tabs Filters and Everywhere. Save and reload. Restrictions are added on top of the standard access rights. Members of the Access Control Manager group and the administrator are never restricted.

What is different from the standard groups: it works per user, per field and per record filter, it hides single buttons and tabs, it controls export and import, and it needs no custom views. Blocking create, edit and delete, record filters, read-only users, export and import guards and posting guards are enforced on the server. Menus, buttons, tabs and filters are hidden in the screens.

## Feature list
- Rules for users and user groups, optionally per company
- Hide menus
- Block create, edit and delete per model
- Hide and refuse archive, duplicate, export, import and add property
- Chatter control: hide chatter, send message, log note and schedule activity
- Field control: invisible, read-only, required, no external link, no create, hide in kanban, not exportable
- Conditions on records and optional enforcement on the server
- Record filters per operation, with Own and Subordinates
- Hide buttons, tabs, filters and group-by options
- Hide view types, reports and bound actions
- Read-Only User
- Disable developer mode, disable login, hide the Apps menu button
- Search bar control: filter button, custom filter, custom group
- Access Control Manager group, never restricted

## Keywords
access control, user access, field access, hide fields, hide menu, read only user, hide buttons, record rules, restrict export, security, permissions

## Technical specifications
- Technical name: axsync_user_access_control
- Version: 20.0.1.0.0
- Category: Extra Tools
- License: OPL-1
- Depends: base, web, mail
- Implementation: restrictions added through the standard access check, record rule computation, view post-processing and web client patches; no changes to standard files
- Testing: automated tests on Odoo 20.0 and checks in the web client. Odoo 20.0 is a development branch at the time of this release; the module follows the 20.0 sources and will be kept in step with the stable release.

## Supported versions
Odoo 20.0.

## Pricing
Price: 85.00 USD (one-time, per Odoo Apps Store terms).

## Publisher information
Published by AXSync. Website: https://www.axsync.com

## Support information
Email hunain@axsync.com, or use Contact the Author on the Apps Store page. Include Odoo version, module version and a description of the issue. See SUPPORT.md.
