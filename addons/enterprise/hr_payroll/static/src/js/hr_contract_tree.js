odoo.define('hr_payroll.hr_contract_tree', function (require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');

    var viewRegistry = require('web.view_registry');
    var ListView = require('web.ListView');
    var ListController = require('web.ListController');

    var _t = core._t;
    var QWeb = core.qweb;

    var IndexWageButton = {
        /**
         * @override
         */
        renderButtons: function() {
            this._super.apply(this, arguments);
            this.$buttons.append(this._renderIndexContractButton());
        },

        /*
            Private
        */
       _renderIndexContractButton: function() {
            return $(QWeb.render('ContractListView.index_button', {})).on('click', this._onIndexWage.bind(this));
       },

        _indexWage: function () {
            return this.do_action('hr_payroll.action_hr_payroll_index', {
                additional_context: {
                    active_ids: this.getSelectedIds(),
                },
            });
        },

        _onIndexWage: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._indexWage();
        },
    };

    var HrContractTreeController = ListController.extend(IndexWageButton);

    var HrContractListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: HrContractTreeController,
        }),
    });

    viewRegistry.add('hr_contract_tree', HrContractListView);

    return HrContractListView;
});
