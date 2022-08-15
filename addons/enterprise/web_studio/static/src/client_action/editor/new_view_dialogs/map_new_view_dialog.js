/** @odoo-module */
import { NewViewDialog } from "@web_studio/client_action/editor/new_view_dialogs/new_view_dialog";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class MapNewViewDialog extends NewViewDialog {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.bodyTemplate = "web_studio.MapNewViewFieldsSelector";
    }

    get viewType() {
        return "map";
    }

    computeSpecificFields(fields) {
        this.partnerFields = fields.filter(
            (field) => field.type === "many2one" && field.relation === "res.partner"
        );
        if (!this.partnerFields.length) {
            this.dialog.add(AlertDialog, {
                body: this.env._t("Contact Field Required"),
                contentClass: "o_web_studio_preserve_space",
            });
            this.close();
        }
    }
}
MapNewViewDialog.props = Object.assign(Object.create(NewViewDialog.props), {
    viewType: { type: String, optional: true },
});
