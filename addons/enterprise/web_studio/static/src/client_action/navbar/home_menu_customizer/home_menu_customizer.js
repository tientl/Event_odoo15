/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FileInput } from "@web/core/file_input/file_input";

export class HomeMenuCustomizer extends owl.Component {
    setup() {
        this.rpc = useService("rpc");
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.company = useService("company");
        this.user = useService("user");
        this.actionManager = useService("action");
        this.menus = useService("menu");
        this.dialogManager = useService("dialog");
        this.bgImageUploaded = this.bgImageUploaded.bind(this); // is executed as a callback
    }

    async bgImageUploaded(ev) {
        const file = ev.detail.files[0];

        if (!file) {
            this.notification.add(this.env._t("Could not change the background"), {
                sticky: true,
                type: "warning",
            });
        } else {
            this.ui.block();
            try {
                await this._setBackgroundImage(file.id);
                browser.location.reload();
            } finally {
                this.ui.unblock();
            }
        }
    }

    _setBackgroundImage(attachment_id) {
        return this.rpc("/web_studio/set_background_image", {
            attachment_id: attachment_id,
            context: this.user.context,
        });
    }
    /**
     * Export all customizations done by Studio in a zip file containing Odoo
     * modules.
     */
    _export() {
        download({ url: "/web_studio/export", data: {} });
    }
    /**
     * Open a dialog allowing to import new modules
     * (e.g. exported customizations).
     */
    _import() {
        const action = {
            name: "Import modules",
            res_model: "base.import.module",
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            target: "new",
            context: {
                dialog_size: "medium",
            },
        };
        const options = {
            onClose: () => this.menus.reload(),
        };
        this.actionManager.doAction(action, options);
    }

    async _resetBgConfirmed() {
        this.ui.block();
        try {
            await this.rpc("/web_studio/reset_background_image", {
                context: this.user.context,
            });
            browser.location.reload();
        } finally {
            this.ui.unblock();
        }
    }

    _resetBgImage() {
        this.dialogManager.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to reset the background image?"),
            title: this.env._t("Confirmation"),
            confirm: () => this._resetBgConfirmed(),
        });
    }
}
HomeMenuCustomizer.template = "web_studio.HomeMenuCustomizer";
HomeMenuCustomizer.components = { FileInput };
