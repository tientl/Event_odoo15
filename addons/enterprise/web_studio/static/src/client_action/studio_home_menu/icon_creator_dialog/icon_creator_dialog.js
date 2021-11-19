/* @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { IconCreator } from "@web_studio/client_action/icon_creator/icon_creator";
import { useService } from "@web/core/utils/hooks";

export class IconCreatorDialog extends Dialog {
    setup() {
        super.setup();
        this.user = useService("user");
        this.rpc = useService("rpc");
        this.menus = useService("menu");
        this.initialAppData = Object.assign({}, this.props.editedAppData);
        this.editedAppData = owl.hooks.useState(this.props.editedAppData);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    onIconChanged(ev) {
        for (const key in this.editedAppData) {
            delete this.editedAppData[key];
        }
        for (const key in ev.detail) {
            this.editedAppData[key] = ev.detail[key];
        }
    }

    /**
     * @private
     */
    async saveIcon() {
        const { type } = this.initialAppData;
        const appId = this.props.appId;
        let iconValue;
        if (this.editedAppData.type !== type) {
            // different type
            if (this.editedAppData.type === "base64") {
                iconValue = this.editedAppData.uploaded_attachment_id;
            } else {
                const { iconClass, color, backgroundColor } = this.editedAppData;
                iconValue = [iconClass, color, backgroundColor];
            }
        } else if (this.editedAppData.type === "custom_icon") {
            // custom icon changed
            const { iconClass, color, backgroundColor } = this.editedAppData;
            if (
                this.initialAppData.iconClass !== iconClass ||
                this.initialAppData.color !== color ||
                this.initialAppData.backgroundColor !== backgroundColor
            ) {
                iconValue = [iconClass, color, backgroundColor];
            }
        } else if (this.editedAppData.uploaded_attachment_id) {
            // new attachment
            iconValue = this.editedAppData.uploaded_attachment_id;
        }

        if (iconValue) {
            await this.rpc("/web_studio/edit_menu_icon", {
                context: this.user.context,
                icon: iconValue,
                menu_id: appId,
            });
            await this.menus.reload();
        }
        this.close();
    }
}
IconCreatorDialog.title = _lt("Edit Application Icon");
IconCreatorDialog.contentClass = "o_web_studio_edit_menu_icon_modal";
IconCreatorDialog.size = "modal-md";
IconCreatorDialog.bodyTemplate = "web_studio.IconCreatorDialogBody";
IconCreatorDialog.footerTemplate = "web_studio.IconCreatorDialogFooter";
IconCreatorDialog.components = { IconCreator };
