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

const HIDE_SELECTORS = {
    apps_menu: ".o_navbar_apps_menu",
    filter_button: ".o_filter_menu",
    custom_filter: ".o_add_custom_filter_menu",
    custom_group: ".o_add_custom_group_menu",
    send: ".o_ChatterTopbar_buttonSendMessage",
    note: ".o_ChatterTopbar_buttonLogNote",
    activity: ".o_ChatterTopbar_buttonScheduleActivity",
    chatter: ".o_Chatter, .o_ChatterContainer",
};

const ITEM_FLAG = {
    archive: "archive",
    unarchive: "archive",
    duplicate: "duplicate",
    delete: "delete",
    export: "export",
};

function filterItems(result, resModel) {
    const model = modelFlags[resModel] || {};
    if (!result || !Array.isArray(result.other)) {
        return result;
    }
    result.other = result.other.filter((item) => {
        const flag = ITEM_FLAG[item.key];
        if (!flag) {
            return true;
        }
        return !(model[flag] || (flag === "export" && globalFlags.export) ||
            (globalFlags.read_only && ["archive", "duplicate", "delete"].includes(flag)));
    });
    return result;
}

if (Object.keys(flags).length) {
    patch(FormController.prototype, "axsync_access_form", {
        getActionMenuItems() {
            return filterItems(this._super(...arguments), this.props.resModel);
        },
    });
    patch(ListController.prototype, "axsync_access_list", {
        getActionMenuItems() {
            return filterItems(this._super(...arguments), this.props.resModel);
        },
    });
    registry.category("services").add("axsync_access", {
        start() {
            // The legacy web client rewrites the class of the body, so plain style rules are used here.
            const rules = [];
            for (const [key, selector] of Object.entries(HIDE_SELECTORS)) {
                if (globalFlags[key]) {
                    rules.push(`${selector} { display: none !important; }`);
                }
            }
            if (rules.length) {
                const style = document.createElement("style");
                style.textContent = rules.join("\n");
                document.head.appendChild(style);
            }
        },
    });
}
