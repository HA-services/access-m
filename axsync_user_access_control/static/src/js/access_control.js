/** @odoo-module **/
// Part of AXSync. See LICENSE file for full copyright and licensing details.
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";

const flags = session.axsync_access || {};
const globalFlags = flags.global || {};
const modelFlags = flags.models || {};

const BODY_CLASSES = {
    apps_menu: "axsync-no-apps-menu",
    filter_button: "axsync-no-filter-button",
    custom_filter: "axsync-no-custom-filter",
    custom_group: "axsync-no-custom-group",
    add_property: "axsync-no-add-property",
    send: "axsync-no-send",
    note: "axsync-no-note",
    activity: "axsync-no-activity",
    chatter: "axsync-no-chatter",
};

const ITEM_FLAG = {
    archive: "archive",
    unarchive: "archive",
    duplicate: "duplicate",
    delete: "delete",
    export: "export",
    addPropertyFieldValue: "add_property",
};

function filterItems(items, resModel) {
    const model = modelFlags[resModel] || {};
    for (const key of Object.keys(items)) {
        const flag = ITEM_FLAG[key];
        if (!flag) {
            continue;
        }
        if (model[flag] || (flag === "export" && globalFlags.export) ||
            (flag === "add_property" && globalFlags.add_property) ||
            (globalFlags.read_only && ["archive", "duplicate", "delete"].includes(flag))) {
            delete items[key];
        }
    }
    return items;
}

if (Object.keys(flags).length) {
    patch(FormController.prototype, {
        getStaticActionMenuItems() {
            return filterItems(super.getStaticActionMenuItems(...arguments), this.props.resModel);
        },
    });
    patch(ListController.prototype, {
        getStaticActionMenuItems() {
            return filterItems(super.getStaticActionMenuItems(...arguments), this.props.resModel);
        },
    });
    registry.category("services").add("axsync_access", {
        start() {
            for (const [key, cls] of Object.entries(BODY_CLASSES)) {
                if (globalFlags[key]) {
                    document.body.classList.add(cls);
                }
            }
        },
    });
}
