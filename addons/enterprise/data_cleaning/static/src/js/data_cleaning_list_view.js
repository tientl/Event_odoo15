odoo.define('data_cleaning.ListView', function (require) {
"use strict";

    var ListView = require('web.ListView');
    var session = require('web.session');
    var viewRegistry = require('web.view_registry');
    var DataCommonListController = require('data_cleaning.CommonListController');

    var DataCleaningListController = DataCommonListController.extend({
        buttons_template: 'DataCleaning.buttons',
        /**
         * @override
         */
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            this.$buttons.on('click', '.o_data_cleaning_validate_button', this._onValidateClick.bind(this));
            this.$buttons.on('click', '.o_data_cleaning_unselect_button', this._onUnselectClick.bind(this));
        },

        /**
         * Validate all the records selected
         * @param {*} ev
         */
        _onValidateClick: async function(ev) {
            const self = this;
            const state = this.model.get(this.handle);
            let record_ids;
            if (this.isDomainSelected) {
                record_ids = await this._domainToResIds(state.getDomain(), session.active_ids_limit);
            } else {
                record_ids = this.getSelectedIds();
            }

            this._rpc({
                model: 'data_cleaning.record',
                method: 'action_validate',
                args: [record_ids],
            }).then(function(data) {
                self.trigger_up('reload');
            });
        },
    });

    var DataCleaningListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: DataCleaningListController,
        }),
    });

    viewRegistry.add('data_cleaning_list', DataCleaningListView);
});
