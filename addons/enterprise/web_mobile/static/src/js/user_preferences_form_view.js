odoo.define('web_mobile.UserPreferencesFormView', function (require) {
    'use strict';

    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');
    const { UpdateDeviceAccountControllerMixin } = require('web_mobile.mixins');

    const UserPreferencesFormView = FormView.extend({
        config: Object.assign({}, FormView.prototype.config, {
            Controller: FormView.prototype.config.Controller.extend(
                UpdateDeviceAccountControllerMixin
            ),
        }),
    });

    viewRegistry.add('res_users_preferences_form', UserPreferencesFormView);

    return UserPreferencesFormView;
});
