odoo.define('documents.DocumentsListModel', function (require) {
'use strict';

/**
 * This file defines the Model for the Documents List view, which is an
 * override of the ListModel.
 */
const ListModel = require('web.ListModel');
const DocumentsModelMixin = require('documents.modelMixin');
const DocumentsViewMixin = require('documents.viewMixin');

const DocumentsListModel = ListModel.extend(DocumentsModelMixin, {

    async loadMissingData({state, ids}) {
        const context = this.loadParams.context;
        const fieldNames = DocumentsViewMixin.inspectorFields.filter(n => n in this.loadParams.fields);
        const extraRecords = await this._rpc({
            model: this.loadParams.modelName,
            method: 'read',
            args: [ids],
            kwargs: {
                fields: fieldNames,
                context: Object.assign(context, {bin_size: true}),
            },
        });
        const dataPoints = extraRecords.map(record => {
            const dataPoint = this._makeDataPoint({
                data: record,
                fields: this.loadParams.fields,
                context: this.loadParams.context,
                fieldsInfo: this.loadParams.fieldsInfo,
                modelName: this.loadParams.modelName,
                parentID: this.loadParams.parentID,
                viewType: this.loadParams.viewType,
                type: 'record',
            });
            this._parseServerData(fieldNames, dataPoint, dataPoint.data)
            return dataPoint;
        })
        state.data = state.data.concat(dataPoints);
    }

});

return DocumentsListModel;

});
