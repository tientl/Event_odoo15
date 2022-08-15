odoo.define('mrp_plm.ToasterButton', function (require) {
    'use strict';

    const widgetRegistry = require('web.widget_registry');
    const Widget = require('web.Widget');
    const core = require("web.core");

    const _t = core._t;

    const ToasterButton = Widget.extend({
        template: 'mrp_plm.ToasterButton',
        xmlDependencies: ['/mrp_plm/static/src/xml/mrp_plm_toaster_button.xml'],
        events: Object.assign({}, Widget.prototype.events, {
            'click .fa-info-circle': '_onClickButton',
        }),

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onClickButton: function (ev) {
            this.displayNotification({ message: _t("Note that a new version of this BOM is available.") });
        },
    });

    widgetRegistry.add('plm_toaster_button', ToasterButton);

    return ToasterButton;
});
