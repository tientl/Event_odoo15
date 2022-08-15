/** @odoo-module **/

    import EmployeeProfileFormView from '@hr/js/language';
    import { UpdateDeviceAccountControllerMixin } from 'web_mobile.mixins';

    EmployeeProfileFormView.prototype.config.Controller.include(UpdateDeviceAccountControllerMixin);
