odoo.define('documents.DocumentsKanbanModel', function (require) {
"use strict";

/**
 * This file defines the Model for the Documents Kanban view, which is an
 * override of the KanbanModel.
 */

const DocumentsModelMixin = require('documents.modelMixin');

const KanbanModel = require('web.KanbanModel');


const DocumentsKanbanModel = KanbanModel.extend(DocumentsModelMixin);

return DocumentsKanbanModel;

});
