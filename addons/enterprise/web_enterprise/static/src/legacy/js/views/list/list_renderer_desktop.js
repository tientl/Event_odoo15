odoo.define('web_enterprise.ListRenderer', function (require) {
    "use strict";

    const config = require('web.config');
    if (config.device.isMobile) {
        return;
    }
    const { qweb } = require('web.core');
    const ListRenderer = require('web.ListRenderer');
    const session = require('web.session');
    const PromoteStudioDialog = require('web_enterprise.PromoteStudioDialog');

    ListRenderer.include({

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This function adds a button at the bottom of the optional
         * columns dropdown menu. This button opens studio if installed and
         * promote studio if not installed.
         *
         * @override
         */
        _renderOptionalColumnsDropdown: function () {
            const $optionalColumnsDropdown = this._super(...arguments);
            if (session.is_system) {
                const $dropdownMenu = $optionalColumnsDropdown.find('.dropdown-menu');
                if (this.optionalColumns.length) {
                    $dropdownMenu.append($("<hr />"));
                }
                const $addCustomField = $(qweb.render('web_enterprise.open_studio_button'));
                $dropdownMenu.append($addCustomField);
                $addCustomField.click(this._onAddCustomFieldClick.bind(this));
            }
            return $optionalColumnsDropdown;
        },

        /**
         * This function returns if the optional columns dropdown menu should be rendered.
         * This function returns true iff there are optional columns or the user is system
         * admin.
         *
         * @override
         */
        _shouldRenderOptionalColumnsDropdown: function () {
            return this._super(...arguments) || session.is_system;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * This function opens studio dialog
         *
         * @param {Event} event
         * @private
         */
        _onAddCustomFieldClick: function (event) {
            event.stopPropagation();
            new PromoteStudioDialog(this).open();
        },
    });
});
