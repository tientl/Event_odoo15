odoo.define('documents.viewMixin', function (require) {
'use strict';

const DocumentsViewMixin = {
    inspectorFields: [
        'active',
        'activity_ids',
        'available_rule_ids',
        'checksum',
        'display_name', // necessary for the mail tracking system to work correctly
        'folder_id',
        'lock_uid',
        'message_attachment_count',
        'message_follower_ids',
        'message_ids',
        'mimetype',
        'name',
        'owner_id',
        'partner_id',
        'previous_attachment_ids',
        'res_id',
        'res_model',
        'res_model_name',
        'res_name',
        'share_ids',
        'tag_ids',
        'type',
        'url',
    ],
    /**
     * @override
     * @param {Object} viewInfo unused
     * @param {Object} [param1={}]
     * @param {Object} [param1.controllerState={}]
     * @param {integer[]} [param1.controllerState.selectedRecordIds]
     */
    init(viewInfo, { controllerState: { selectedRecordIds, }={}, }={}) {
        this._super(...arguments);
        // force the presence of a searchpanel in Documents
        this.withSearchPanel = true;
        this.rendererParams.withSearchPanel = true;
        this.controllerParams.selectedRecordIds = selectedRecordIds;

        // add the fields used in the DocumentsInspector to the list of fields to fetch
        _.defaults(this.fieldsInfo[this.viewType], _.pick(this.fields, this.inspectorFields));

        // force fetch of relational data (display_name and tooltip) for related
        // rules to display in the DocumentsInspector
        this.fieldsInfo[this.viewType].available_rule_ids = Object.assign({}, {
            fieldsInfo: {
                default: {
                    display_name: {},
                    note: {},
                    limited_to_single_record: {},
                    create_model: {},
                },
            },
            relatedFields: {
                display_name: {type: 'string'},
                note: {type: 'string'},
                limited_to_single_record: {type: 'boolean'},
                create_model: {type: 'string'},
            },
            viewType: 'default',
        }, this.fieldsInfo[this.viewType].available_rule_ids);
    },

};

return DocumentsViewMixin;

});
