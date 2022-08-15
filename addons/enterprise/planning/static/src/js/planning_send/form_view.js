/** @odoo-module **/

import view_registry from 'web.view_registry';
import FormView from 'web.FormView';
import Model from './form_model';
import Controller from './form_controller';

const PlanningSendFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Model,
        Controller,
    }),
});

view_registry.add('planning_send_form', PlanningSendFormView);

export default PlanningSendFormView;
