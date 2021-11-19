odoo.define('documents.DocumentsListModel', function (require) {
'use strict';

/**
 * This file defines the Model for the Documents List view, which is an
 * override of the ListModel.
 */
const ListModel = require('web.ListModel');
const DocumentsModelMixin = require('documents.modelMixin');

const DocumentsListModel = ListModel.extend(DocumentsModelMixin);

return DocumentsListModel;

});
