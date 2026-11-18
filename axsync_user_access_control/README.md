# AXSync User Access Control

Odoo 20.0 | Category: Extra Tools | License: OPL-1 | Publisher: AXSync (www.axsync.com)

Decide what each user or group sees and does in Odoo, without code: hide menus, fields, buttons, tabs and filters, block create, edit, delete, export and import, limit records, make users read-only, switch off developer mode or the login.

## Requirements

- Odoo 20.0 with the base, web and Discuss (`mail`) modules. Nothing else is needed and no Python library is added.

## Installation

1. Copy the `axsync_user_access_control` folder into a directory on your Odoo `addons_path` (or add the Git repository branch `20.0` on Odoo.sh).
2. Restart Odoo and update the Apps list (developer mode, Apps, Update Apps List).
3. Install **User Access Control**.

Installing changes nothing for anyone until a rule is created.

## Access

- The group **Access Control Manager** (Settings, Users, Access Control) can create and change rules. The Administration Settings group includes it.
- Members of Access Control Manager and the administrator are never restricted by a rule. This is deliberate, so nobody can lock themselves out.

## Using the module

Open Access Control > Rules and create a rule.

1. Choose who: users, user groups, or both. Optionally choose companies; the rule then applies only while one of them is the current company.
2. Use the tabs:
   - **Menus**: menus the users do not see.
   - **Models**: per model switches (create, edit, delete, archive, duplicate, export, import, add property, chatter, view types, reports, actions).
   - **Fields**: invisible, read-only, required and relational field options, with an optional condition.
   - **Records**: extra record filters per operation, including Own and Subordinates.
   - **Buttons, Tabs, Filters**: hide single elements of the views of a model.
   - **Everywhere**: switches for all models.
3. Save. The restrictions apply the next time the user loads a screen. A browser refresh is the safe way to make sure.

The whole-user switches on the rule: Read-Only User, Disable Developer Mode, Disable Login, Hide the Apps Menu Button.

### Fields

Invisible, Read-Only and Required act on form, list and kanban views. A condition such as `[("state", "=", "done")]` makes the behaviour apply only to matching records. Conditions support fields of the same model, the operators `=`, `!=`, `in`, `not in`, `<`, `>`, `<=` and `>=`, and the logical operators. **Also Enforce on the Server** makes Read-Only reject writes and Required reject empty saves, even from imports or other code. Invisible fields are blanked in the data the user's session receives.

### Records

A record filter is a normal Odoo domain, evaluated for the user (`user`, `uid`, `company_ids`, `time` and `datetime` are available). Tick Read, Edit, Create or Delete to choose what it limits. Untick Read for a soft restriction: the user sees the records but cannot change the filtered ones. **Own and Subordinates** adds the people who report to the user, through the Reports To field on the user form.

### Buttons, Tabs and Filters

Use Reload Elements from Views to list the buttons, tabs, filters and group-by options found in the views of the model, then select the ones to hide. A condition can make a button or tab disappear only for matching records.

## What is enforced where

- **On the server**: blocking create, edit and delete, read-only users, record filters, hiding of invisible fields in the data, duplicate, archive, export and import guards, posting messages, notes and activities, printing hidden reports, disabled login, developer mode, and the Read-Only enforcement and Required enforcement when Also Enforce on the Server is ticked.
- **In the screens (hiding only)**: menus, buttons, tabs, filters, group-by options, view types, bound actions, the Add Custom Filter and Add Custom Group entries, the Apps menu button, the chatter, and Read-Only and Required without server enforcement. A user who calls the Odoo API directly is not stopped by a purely visual restriction. To protect data, use the model switches, the Records tab or Also Enforce on the Server.

## Limits

- Read-Only Users can still write the technical records Odoo needs to keep a session working: presence, login logs, notification state, user settings, saved filters and attachments.
- Hidden menus are not access rights. The user can still reach the model by other routes unless the model is also blocked.
- The list of fields in the export dialog is not filtered. A field marked Not Exportable is rejected when the export runs.
- A field hidden in a kanban card by a code expression is blanked in the data only when Invisible is unconditional.
- Conditions support simple fields of the same model. Related fields (`partner_id.name`) are not supported.
- Views of other applications can differ between versions. Use Reload Elements from Views after installing or updating applications.
- The Spreadsheet application is not covered.
- Texts and labels are in English and can be translated with the standard Odoo translation tools.
- Works with Odoo. Odoo 20.0 is a development branch at the time of this release; the module follows the 20.0 sources and will be kept in step with the stable release.
