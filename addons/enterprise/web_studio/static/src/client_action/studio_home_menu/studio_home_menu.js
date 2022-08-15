/** @odoo-module **/
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { useService } from "@web/core/utils/hooks";
import { NotEditableActionError } from "../../studio_service";
import { IconCreatorDialog } from "./icon_creator_dialog/icon_creator_dialog";

const NEW_APP_BUTTON = {
    isNewAppButton: true,
    label: "New App",
    webIconData: "/web_studio/static/src/img/default_icon_app.png",
};

/**
 * Studio home menu
 *
 * Studio version of the standard enterprise home menu. It has roughly the same
 * implementation, with the exception of the app icon edition and the app creator.
 * @extends HomeMenu
 */
export class StudioHomeMenu extends HomeMenu {
    /**
     * @param {Object} props
     * @param {Object[]} props.apps application icons
     * @param {string} props.apps[].action
     * @param {number} props.apps[].id
     * @param {string} props.apps[].label
     * @param {string} props.apps[].parents
     * @param {(boolean|string|Object)} props.apps[].webIcon either:
     *      - boolean: false (no webIcon)
     *      - string: path to Odoo icon file
     *      - Object: customized icon (background, class and color)
     * @param {string} [props.apps[].webIconData]
     * @param {string} props.apps[].xmlid
     */
    constructor() {
        super(...arguments);

        this.user = useService("user");
        this.studio = useService("studio");
        this.notifications = useService("notification");
        this.dialog = useService("dialog");
    }

    mounted() {
        super.mounted();
        this.canEditIcons = true;
        this.el.classList.add("o_studio_home_menu");
    }

    async willUpdateProps(nextProps) {
        this.availableApps = this.state.query.length
            ? this._filter(nextProps.apps)
            : nextProps.apps;
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    get displayedApps() {
        return super.displayedApps.concat([NEW_APP_BUTTON]);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async _openMenu(menu) {
        if (menu.isNewAppButton) {
            this.canEditIcons = false;
            return this.studio.open(this.studio.MODES.APP_CREATOR);
        } else {
            try {
                await this.studio.open(this.studio.MODES.EDITOR, menu.actionID);
                this.menus.setCurrentMenu(menu);
            } catch (e) {
                if (e instanceof NotEditableActionError) {
                    const options = { type: "danger" };
                    this.notifications.add(
                        this.env._t("This action is not editable by Studio"),
                        options
                    );
                    return;
                }
                throw e;
            }
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} app
     */
    onEditIconClick(app) {
        if (!this.canEditIcons) {
            return;
        }
        const editedAppData = {};
        if (app.webIconData) {
            Object.assign(editedAppData, {
                webIconData: app.webIconData,
                type: "base64",
            });
        } else {
            Object.assign(editedAppData, {
                backgroundColor: app.webIcon.backgroundColor,
                color: app.webIcon.color,
                iconClass: app.webIcon.iconClass,
                type: "custom_icon",
            });
        }

        const dialogProps = {
            editedAppData,
            appId: app.id,
        };
        this.dialog.add(IconCreatorDialog, dialogProps);
    }
}

StudioHomeMenu.props = { apps: HomeMenu.props.apps };
StudioHomeMenu.template = "web_studio.StudioHomeMenu";
