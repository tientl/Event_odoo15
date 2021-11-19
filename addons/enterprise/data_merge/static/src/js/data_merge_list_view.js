odoo.define('data_merge.ListView', function (require) {
"use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var ListController = require('web.ListController');
    var ListRenderer = require('web.ListRenderer');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var DataCommonListController = require('data_cleaning.CommonListController');
    var _t = core._t;


    var DataMergeListController = DataCommonListController.extend({
        custom_events: _.extend({}, DataCommonListController.prototype.custom_events, {
            merge_records: '_onMergeDiscardRecords',
            discard_records: '_onMergeDiscardRecords',
            field_changed: '_onFieldChanged',
        }),

        buttons_template: 'DataMergeListView.buttons',

        _onFieldChanged: function (event) {
            var self = this;
            this._super.apply(this, arguments);
            setTimeout(function() { self.trigger_up('reload'); });
        },

        /**
         * @override
         */
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            this.$buttons.on('click', '.o_data_merge_merge_button', this._onMergeClick.bind(this));
            this.$buttons.on('click', '.o_data_merge_unselect_button', this._onUnselectClick.bind(this));
        },

        /**
         * Get the list of selected records for the specified group
         * @returns list of record IDs
         * @param {int} group_id
         */
        _getGroupRecords: function(group_id) {
            let records = this.getSelectedRecords();
            const group_records = records.filter(record => record.data.group_id === group_id);

            return group_records;
        },

        /**
         * Get the original record IDs
         * @param {int[]} records
         */
        _getRecordIDS: function(records) {
            return records.map(record => parseInt(record.res_id));
        },

        /**
         * Call the specified action
         * @param {string} action Action to perform (merge/discard)
         * @param {int} group_id ID of the data_merge.group
         * @param {int[]} record_ids Selected records to merge/discard
         * @param {bool} show_discarded Flag to indicate if the "show discarded" filter is active
         */
        _callAction: function(action, group_id, record_ids, show_discarded) {
            return this._rpc({
                model: 'data_merge.group',
                method: action,
                args: [group_id, record_ids],
                context: {'show_discarded': show_discarded},
            });
        },

        /**
         * Merge all the selected records
         * @param {*} ev
         */
        _onMergeClick: function(ev) {
            const records = this.getSelectedRecords();
            const self = this;
            let group_ids = {};
            const context = this.renderer.state.context;
            const discard_view = context && context.show_discarded?context.show_discarded:false;

            records.forEach(function(record) {
                const group_id = parseInt(record.data.group_id);
                let ids = group_ids[group_id] || [];
                ids.push(parseInt(record.res_id));
                group_ids[group_id] = ids;
            });

            const message = _.str.sprintf(_t("Are you sure that you want to merge the selected records in their respective group?"));

            Dialog.confirm(self, message, {
                confirm_callback: function () {
                    self._callAction('merge_multiple_records', null, group_ids, discard_view).then(function () {
                        self._showMergeNotification();
                        self.trigger_up('reload');
                    });
                }
            });
        },

        /**
         * Merge or discard the selected records for the 'record group'
         * @param {*} ev
         */
        _onMergeDiscardRecords: function(ev) {
            const record = ev.data.record;
            const group_records = this._getGroupRecords(record.res_id);
            const group_id = record.res_id;
            const record_ids = this._getRecordIDS(group_records);
            const self = this;
            const action = (ev.name === 'merge_records' ? 'merge_records' : 'discard_records');

            const discard_view = record.context && record.context.show_discarded?record.context.show_discarded:false;
            if (action === 'merge_records') {
                const message = _t("Are you sure that you want to merge these records?");
                Dialog.confirm(self, message, {
                    confirm_callback: function () {

                        self._doActionMergeDiscard(action, group_id, record_ids, discard_view);
                    }
                });
            }
            else {
                self._doActionMergeDiscard(action, group_id, record_ids, discard_view);
            }
        },

        _doActionMergeDiscard: function(action, group_id, record_ids, discard_view) {
            const self = this;
            this._callAction(action, group_id, record_ids, discard_view).then(function (res) {
                if(res && 'type' in res && res.type.startsWith('ir.actions')) {
                    if(!('views' in res)) {
                        res = _.extend(res, {
                            views: [[false, 'form']]
                        });
                    }

                    self.do_action(res);
                } else if (res && res.back_to_model) {
                    window.history.back();
                } else {
                    if(action === 'merge_records') {
                        const records_merged = res && 'records_merged' in res ? res.records_merged : 'The selected';
                        self._showMergeNotification(records_merged);
                    }
                    self.trigger_up('reload');
                }
            });
        },

        /**
         * Show a notification with the number of records merged
         * @param {int} records_merged
         */
        _showMergeNotification: function(records_merged) {
            this.displayNotification({
                message: _.str.sprintf(_t("%s records have been merged"), records_merged?records_merged:_t('The selected')),
                type: 'info'
            });
        }
    });

    var DataMergeListRenderer = ListRenderer.extend({
        /**
         * @override
         */
        _onGroupButtonClicked: function (record, node, ev) {
            ev.stopPropagation();
            if(node.attrs.name === 'merge_records') {
                this.trigger_up('merge_records', { record: record });
            } else if(node.attrs.name === 'discard_records') {
                this.trigger_up('discard_records', { record: record });
            } else {
                this._super.apply(this, arguments);
            }
        },

        /**
         * Hide the "Discard" button when the "Discarded" filter is active
         * @override
         */
        _renderGroupButton: function (list, node) {
            var res = this._super.apply(this, arguments);

            if('show_discarded' in list.context && list.context.show_discarded) {
                if(node.attrs.name === 'discard_records') {
                    res.css('display', 'none');
                }
            }
            return res;
        }
    });

    var DataMergeListView = ListView.extend({
       config: _.extend({}, ListView.prototype.config, {
            Controller: DataMergeListController,
            Renderer: DataMergeListRenderer,
        }),
    });

    viewRegistry.add('data_merge_list', DataMergeListView);
});
