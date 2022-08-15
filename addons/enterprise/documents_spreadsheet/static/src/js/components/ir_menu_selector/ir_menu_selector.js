/** @odoo-module */

import { ComponentAdapter } from "web.OwlCompatibility";
import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { StandaloneMany2OneField } from "../../widgets/standalone_many2one_field";
const { xml, css } = owl.tags;
const { useState, useExternalListener } = owl.hooks;

const STYLE = css/* scss */ `
    .o-ir-menu-selector .o_field_many2one {
        width: 100%;
    }
`;

class MenuSelectorWidgetAdapter extends ComponentAdapter {
    setup() {
        this.env = owl.Component.env;
    }

    mounted() {
        this.widget.getFocusableElement().focus();
    }

    /**
     * @override
     */
    get widgetArgs() {
        const domain = [
            ["action", "!=", false],
            ["id", "in", this.props.availableMenuIds],
        ]
        const attrs = {
            placeholder: this.env._t("Select a menu..."),
            string: this.env._t("Menu Items"),
        };
        return ["ir.ui.menu", this.props.menuId, domain, attrs];
    }
}

export class IrMenuSelector extends Dialog {
    setup() {
        super.setup();
        this.StandaloneMany2OneField = StandaloneMany2OneField;
        this.menus = useService("menu");
        this.orm = useService("orm");
        this.selectedMenu = useState({
            id: undefined,
        });
        // Clicking anywhere will close the link editor menu. It should be
        // prevented otherwise the chain of event would be broken.
        // A solution would be to listen all clicks coming from this dialog and stop
        // their propagation.
        // However, the autocomplete dropdown of the Many2OneField widget is *not*
        // a child of this component. It's actually a direct child of "body" ¯\_(ツ)_/¯
        // The following external listener handles this.
        useExternalListener(document.body, "click", (ev) => ev.stopPropagation())
    }

    get availableMenuIds() {
        return this.menus.getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
    }

    _onConfirm() {
        this.props.onMenuSelected(this.selectedMenu.id);
    }
    _onValueChanged(ev) {
        this.selectedMenu.id = ev.detail.value;
    }
}
IrMenuSelector.components = { MenuSelectorWidgetAdapter };
IrMenuSelector.style = STYLE;
IrMenuSelector.title = _lt("Select an Odoo menu to link in your spreadsheet");
IrMenuSelector.size = "model-sm";

IrMenuSelector.bodyTemplate = xml/* xml */ `
    <MenuSelectorWidgetAdapter
        class="o-ir-menu-selector"
        t-on-click.stop=""
        Component="StandaloneMany2OneField"
        menuId="props.menuId"
        availableMenuIds="availableMenuIds"
        t-on-value-changed="_onValueChanged"
    />
`;
IrMenuSelector.footerTemplate = "documents_spreadsheet.IrMenuSelectorFooter";
