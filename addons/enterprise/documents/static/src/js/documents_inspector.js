odoo.define('documents.DocumentsInspector', function (require) {
'use strict';

/**
 * This file defines the DocumentsInspector Widget, which is displayed next to
 * the KanbanRenderer in the DocumentsKanbanView.
 */

const { _t, qweb } = require('web.core');
const {Markup} = require('web.utils');
const fieldRegistry = require('web.field_registry');
const session = require('web.session');
const { str_to_datetime } = require('web.time');
const dialogs = require('web.view_dialogs');
const Widget = require('web.Widget');
const StandaloneFieldManagerMixin = require("web.StandaloneFieldManagerMixin");

const TAGS_SEARCH_LIMIT = 8;

const DocumentsInspector = Widget.extend(StandaloneFieldManagerMixin, {
    template: 'documents.DocumentsInspector',
    custom_events: _.extend({}, StandaloneFieldManagerMixin.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    events: {
        'click .o_inspector_archive': '_onArchive',
        'click .o_inspector_request_icon': '_onClickRequestIcon',
        'click .o_inspector_delete': '_onDelete',
        'click .o_inspector_download': '_onDownload',
        'click .o_inspector_replace': '_onReplace',
        'click .o_inspector_split': '_onClickSplit',
        'click .o_inspector_history_item_delete': '_onClickHistoryItemDelete',
        'click .o_inspector_history_item_download': '_onClickHistoryItemDownload',
        'click .o_inspector_history_item_restore': '_onClickHistoryItemRestore',
        'click .o_inspector_lock': '_onLock',
        'click .o_inspector_share': '_onShare',
        'click .o_inspector_open_chatter': '_onOpenChatter',
        'click .o_inspector_tag_add': '_onTagInputClicked',
        'click .o_inspector_tag_remove': '_onRemoveTag',
        'click .o_inspector_trigger_rule': '_onTriggerRule',
        'click .o_inspector_object_name': '_onOpenResource',
        'click .o_preview_available': '_onOpenPreview',
        'click .o_document_pdf': '_onOpenPDF',
        'click .o_inspector_model_edit': '_onEditModel',
        'click .o_inspector_model_delete': '_onDeleteModel',
        'mouseover .o_inspector_trigger_hover': '_onMouseoverRule',
        'mouseout .o_inspector_trigger_hover': '_onMouseoutRule',
    },

    /**
     * @override
     * @param {Object} params
     * @param {Array} params.recordIds list of document's resIds
     * @param {Object} params.state
     */
    init: function (parent, params) {
        this._super(...arguments);
        StandaloneFieldManagerMixin.init.call(this, parent.model);

        this._viewType = params.viewType;
        this.nbDocuments = params.state.count;
        this.size = params.state.size;
        this.focusTagInput = params.focusTagInput;
        this.currentFolder = _.findWhere(params.folders, {id: params.folderId});
        if (this.currentFolder && this.currentFolder['description']) {
            this.currentFolder.description = Markup(this.currentFolder['description']);
        }
        this.recordsData = {};
        this.shareAliases = params.shareAliases;

        this.records = [];
        for (const resId of params.recordIds) {
            const record = params.state.data.find(record => record.res_id === resId);
            if (record) {
                let youtubeToken;
                let youtubeUrlMatch;
                if (record.data.url && record.data.url.length) {
                    /** youtu<A>/<B><token>
                     * A = .be|be.com
                     * B = watch?v=|''
                     * token = <11 case sensitive alphanumeric characters and _>
                     */
                    youtubeUrlMatch = record.data.url.match('youtu(?:\.be|be\.com)/(?:.*v(?:/|=)|(?:.*/)?)([a-zA-Z0-9-_]{11})');
                }
                if (youtubeUrlMatch && youtubeUrlMatch.length > 1) {
                     youtubeToken = youtubeUrlMatch[1];
                }
                this.recordsData[record.id] = {
                    isGif: new RegExp('image.*(gif)').test(record.data.mimetype),
                    isImage: new RegExp('image.*(jpeg|jpg|png)').test(record.data.mimetype),
                    isYouTubeVideo: !!youtubeToken,
                    youtubeToken,
                };
                this.records.push(record);
            }
        }
        this.tags = params.tags;
        const tagIdsByRecord = this.records.map(record => record.data.tag_ids.res_ids);
        this.commonTagIds = _.intersection(...tagIdsByRecord);
        const ruleIdsByRecord = this.records.map(record => record.data.available_rule_ids.res_ids);
        const commonRuleIds = _.intersection.apply(_, ruleIdsByRecord);
        const record = this.records[0];
        this._rules = commonRuleIds.map(ruleId => {
            const rule = record.data.available_rule_ids.data.find(record => record.res_id === ruleId);
            return rule.data;
        });

        // we have to block some actions (like opening the record preview) when
        // there are pending 'multiSave' requests
        this.pendingSavingRequests = 0;

        this._isLocked = this.records.some(record =>
             record.data.lock_uid && record.data.lock_uid.res_id !== session.uid
        );
        this.isPdfOnly = this.records.every(record => record.data.mimetype === 'application/pdf');
    },
    /**
     * @override
     */
    async start() {
        this._renderTags();
        this._renderHistory();
        this._renderRules();
        this._renderModel();
        this._updateButtons();
        await Promise.all([
            this._renderFields(),
            this._renderHeader(),
            this._super(...arguments)
        ]);
        this.$('.o_inspector_table .o_input').prop('disabled', this._isLocked);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Return the internal state of the widget, which has to be restored after
     * an update (when this instance is destroyed, and another one is created).
     *
     * @returns {Object}
     */
    getLocalState: function () {
        return {
            scrollTop: this.el.scrollTop,
        };
    },
    /**
     * Restore the given state.
     *
     * @param {Object} state
     * @param {integer} state.scrollTop the scroll position to restore
     */
    setLocalState: function (state) {
        this.el.scrollTop = state.scrollTop;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute the classes to use in DocumentsInspector.previews template
     *
     * @param {Object} record
     * @return {String}
     */
    _computeClasses: function (record) {
        const classes = ["o_document_preview"];
        const nbPreviews = this.records.length;
        const recordData = this.recordsData[record.id];
        if (record.data.type === 'empty') {
            classes.push("o_document_request_preview");
        }
        if (nbPreviews === 1) {
            classes.push("o_documents_single_preview");
        }
        if ((recordData.isImage || recordData.isYouTubeVideo)) {
            classes.push("o_documents_preview_image");
        } else {
            classes.push("o_documents_preview_mimetype");
        }
        if ((recordData.isYouTubeVideo || recordData.isGif)) {
            classes.push("o_non_image_preview");
        }
        return classes.join(" ");
    },
    /**
     * Generate the record dataPoint to pass to the FieldMany2one when several
     * records a selected, and when those records have different values for the
     * many2one field to display.
     *
     * @private
     * @param {string} fieldName a many2one field
     */
    _generateCommonRecord: function (fieldName) {
        const record = Object.assign({}, this.records[0], {
            id: null,
            res_id: null,
        });
        record.data = Object.assign({}, record.data);
        record.data[fieldName] = {
            data: {
                display_name: _t('Multiple values'),
                id: null,
            },
        };
        return record;
    },
    /**
     * Render and append a field widget for the given field and the current
     * records.
     *
     * @private
     * @param {string} fieldName
     * @param {Object} [options] options to pass to the field
     * @param {string} [options.icon] optional icon to display
     * @param {string} [options.label] the label to display
     * @return {Promise}
     */
    _renderField: function (fieldName, options) {
        options = options || {};

        // generate the record to pass to the FieldWidget
        const values = _.uniq(this.records.map(record => {
            return record.data[fieldName] && record.data[fieldName].res_id;
        }));
        let record;
        if (values.length > 1) {
            record = this._generateCommonRecord(fieldName);
        } else {
            record = this.records[0];
        }

        const $row = $(qweb.render('documents.DocumentsInspector.infoRow'));

        // render the label
        const $label = $(qweb.render('documents.DocumentsInspector.fieldLabel', {
            icon: options.icon,
            label: options.label || record.fields[fieldName].string,
            name: fieldName,
        }));
        $label.appendTo($row.find('.o_inspector_label'));

        // render and append field
        const type = record.fields[fieldName].type;
        const FieldWidget = fieldRegistry.get(type);
        options = Object.assign({}, options, {
            noOpen: true, // option for many2one fields
            viewType: this._viewType,
        });
        const fieldWidget = new FieldWidget(this, fieldName, record, options);
        fieldWidget.nodeOptions.no_quick_create = true; // nodeOptions for many2one fields
        const prom = fieldWidget.appendTo($row.find('.o_inspector_value')).then(function() {
            fieldWidget.getFocusableElement().attr('id', fieldName);
            if (type === 'many2one' && values.length > 1) {
                fieldWidget.$el.addClass('o_multiple_values');
            }
        });
        $row.insertBefore(this.$('.o_inspector_fields tbody tr.o_inspector_divider'));
        return prom;
    },
    /**
     * @private
     * @return {Promise}
     */
    _renderFields: function () {
        const options = {mode: 'edit'};
        const proms = [];
        if (this.records.length === 1) {
            proms.push(this._renderField('name', options));
            if (this.records[0].data.type === 'url') {
                proms.push(this._renderField('url', options));
            }
        }
        if (this.records.length > 0) {
            proms.push(this._renderField('partner_id', options));
            proms.push(this._renderField('owner_id', options));
            proms.push(this._renderField('folder_id', {
                icon: 'fa fa-folder o_documents_folder_color',
                mode: 'edit',
            }));
        }
        return Promise.all(proms);
    },
    /**
     * @private
     * @return {Promise}
     */
    async _renderHistory() {
        const attachment_ids = this.records.length === 1 ? this.records[0].data.previous_attachment_ids.res_ids : [];
        if (!attachment_ids) {
           return;
        }
        const attachments = await this._rpc({
            model: 'ir.attachment',
            method: 'read',
            args: [attachment_ids, ['name', 'create_date', 'create_uid']],
            orderBy: [{ name: 'create_date', asc: false }],
        });
        $(qweb.render('documents.inspector.attachmentHistory', {
            attachments,
            str_to_datetime,
        })).appendTo(this.$('.o_inspector_history'));
    },
    /**
     * @private
     */
    _renderModel: function () {
        if (this.records.length !== 1) {
           return;
        }
        const resModelName = this.records[0].data.res_model_name;
        if (!resModelName || this.records[0].data.res_model === 'documents.document') {
            return;
        }

        const $modelContainer = this.$('.o_model_container');
        const options = {
            res_model: resModelName,
            res_name: this.records[0].data.res_name,
            is_editable_attachment: false,
        };

        this._rpc({
            model: this.records[0].data.res_model,
            method: 'check_access_rights',
            args: ['write', false]
        }).then((res) => {
            options['is_editable_attachment'] = (res && this.records[0].data.is_editable_attachment && !this._isLocked);
            $modelContainer.append(qweb.render('documents.DocumentsInspector.resModel', options));
        }).catch(() => {
            $modelContainer.append(qweb.render('documents.DocumentsInspector.resModel', options));
        });
    },
    /**
     * @private
     */
    _renderRules: function () {
        if (!this.currentFolder || this._isLocked) {
           return;
        }
        for (const rule of this._rules) {
            if (this.records.length === 1 || !rule.limited_to_single_record) {
                const $rule = $(qweb.render('documents.DocumentsInspector.rule', rule));
                $rule.appendTo(this.$('.o_inspector_rules'));
            }
        }
    },
    /**
     * @private
     */
    _renderTags: function () {
        const $tags = this.$('.o_inspector_tags');

        // render common tags
        const commonTags = this.tags.filter(tag => this.commonTagIds.includes(tag.id));
        for (const tag of commonTags) {
            if (tag) {
                // hide unknown tags (this may happen if a document with tags
                // is moved to another folder, but we keep those tags in case
                // the document is moved back to its original folder)
                const $tag = $(qweb.render('documents.DocumentsInspector.tag', tag));
                $tag.appendTo(this.$('.o_inspector_tags'));
            }
        };

        // render autocomplete input (if there are still tags to add)
        if (this.tags.length > this.commonTagIds.length) {
            this.$tagInput = $('<input>', {
                class: 'o_input o_inspector_tag_add',
                type: 'text',
            }).attr('placeholder', _t("+ Add a tag "));

            this.$tagInput.autocomplete({
                delay: 0,
                minLength: 0,
                autoFocus: true,
                select: (event, ui) => {
                    this.trigger_up('set_focus_tag_input');
                    const currentId = ui.item.id;
                    if (ui.item.special) {
                        if (ui.item.special === 'more') {
                            this._searchMore(this._lastSearchVal);
                        }
                    } else if (currentId) {
                        this._saveMulti({
                            tag_ids: {
                                operation: 'ADD_M2M',
                                resIds: [currentId],
                            },
                        });
                    }
                },
                source: (req, resp) => {
                    resp(this._search(req.term));
                    this._lastSearchVal = req.term;
                },
            });

            const disabled = this._isLocked || (this.records.length === 1 && !this.records[0].data.active);
            $tags.closest('.o_inspector_custom_field').toggleClass('o_disabled', disabled);

            this.$tagInput.appendTo($tags);
            if (this.focusTagInput) {
                this.$tagInput.focus();
            }
        }
    },

    _renderHeader() {
        if (this.shareAliases.length) {
            this.$('.o_folder_description_alias').text(this.shareAliases[0].aliasName)
        }
    },
    /**
     * Trigger a 'save_multi' event to save changes on the selected records.
     *
     * @private
     * @param {Object} changes
     */
    _saveMulti: function (changes) {
        this.pendingSavingRequests++;
        this.trigger_up('save_multi', {
            changes: changes,
            dataPointIds: _.pluck(this.records, 'id'),
            callback: () => {
                this.pendingSavingRequests--;
            },
        });
    },
    /**
     * Search for tags matching the given value. The result is given to jQuery
     * UI autocomplete.
     *
     * @private
     * @param {string} value
     * @returns {Object[]}
     */
    _search: function (value) {
        const tags = [];
        for (const tag of this.tags) {
            // don't search amongst already linked tags
            if (!_.contains(this.commonTagIds, tag.id)) {
                tags.push({
                    id: tag.id,
                    label: tag.group_name + ' > ' + tag.display_name,
                });
            }
        }
        const lowerValue = value.toLowerCase();
        const allSearchResults = tags.filter(tag => tag.label.toLowerCase().includes(lowerValue));
        const searchResults = allSearchResults.slice(0, TAGS_SEARCH_LIMIT);
        if (allSearchResults.length > TAGS_SEARCH_LIMIT) {
            searchResults.push({
                label: _t("Search more..."),
                special: 'more',
                classname: 'o_m2o_dropdown_option',
            });
        }

        return searchResults;
    },
    /**
     * @private
     * @param {Object[]} [dynamicFilters=[]] filters to add to the search view
     *   in the dialog (each filter has keys 'description' and 'domain')
     */
    _searchCreatePopup(dynamicFilters=[]) {
        this.$('.o_inspector_tag_add').val('');
        return new dialogs.SelectCreateDialog(this, {
            domain: [['folder_id', '=', this.currentFolder.id]],
            dynamicFilters: dynamicFilters || [],
            no_create: true,
            on_selected: records => this._saveMulti({
                tag_ids: {
                   operation: 'ADD_M2M',
                   resIds: records.map(record => record.id),
                },
            }),
            res_model: 'documents.tag',
            title: _t('Select tags'),
        }).open();
    },
    /**
     * Search for tags matching the value for either tag.name and tag.facet_id.name.
     *
     * @private
     * @param {String} value
     */
    async _searchMore(value) {
        let results;
        if (value) {
            results = await this._rpc({
                model: 'documents.tag',
                method: 'search_read',
                fields: ['id'],
                domain: ['&', '&',
                            ['id', 'not in', this.commonTagIds],
                            ['folder_id', '=', this.currentFolder.id],
                            '|',
                                ['facet_id.name', 'ilike', value],
                                ['name', 'ilike', value]
                ],
            });
        }
        let dynamicFilters;
        if (results) {
            const ids = results.map(result => result.id);
            dynamicFilters = [{
                description: _.str.sprintf(_t('Name or Category contains: %s'), value),
                domain: [['id', 'in', ids]],
            }];
        }
        await this._searchCreatePopup(dynamicFilters);
    },
    /**
     * Disable buttons if at least one of the selected records is locked by
     * someone else
     *
     * @private
     */
    _updateButtons: function () {
        const binary = this.records.some(record => record.data.type === 'binary');
        if (this._isLocked) {
            this.$('.o_inspector_replace').prop('disabled', true);
            this.$('.o_inspector_delete').prop('disabled', true);
            this.$('.o_inspector_archive').prop('disabled', true);
            this.$('.o_inspector_lock').prop('disabled', true);
            this.$('.o_inspector_split').prop('disabled', true);
            this.$('.o_inspector_table .o_field_widget').prop('disabled', true);
        }
        if (!binary && (this.records.length > 1 || (this.records.length && this.records[0].data.type === 'empty'))) {
            this.$('.o_inspector_download').prop('disabled', true);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onArchive: function () {
        this.trigger_up('archive_records', {
            records: this.records,
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickHistoryItemDelete(ev) {
        this.trigger_up('history_item_delete', {
            attachmentId: $(ev.currentTarget).data('id'),
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickHistoryItemDownload(ev) {
        this.trigger_up('history_item_download', {
            attachmentId: $(ev.currentTarget).data('id'),
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickHistoryItemRestore(ev) {
        this.trigger_up('history_item_restore', {
            resId: this.records[0].res_id,
            attachmentId: $(ev.currentTarget).data('id'),
        });
    },
    /**
     * @private
     */
    _onClickRequestIcon(ev) {
        const documentId = $(ev.currentTarget).data('id');
        this.trigger_up('set_file', {
            id: documentId,
        });
    },
    /**
     * Opens the pdfManager with the currently selected records.
     *
     * @private
     */
    _onClickSplit(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.pendingSavingRequests > 0) {
            return;
        }
        const records = this.records.map(record => record.data);
        this.trigger_up('kanban_image_clicked', {
            recordId: records[0].id,
            recordList: records,
            openPdfManager: true,
        });
    },
    /**
     * @private
     */
    _onDelete: function () {
        this.trigger_up('delete_records', {
            records: this.records,
        });
    },
    /**
     * Remove the link between the document and its record.
     * @param {MouseEvent} ev
     */
    _onDeleteModel: function (ev) {
        this.trigger_up('delete_model', {
            documentId: this.records[0].data['id'],
        });
    },
    /**
     * Download the selected documents (zipped if there are several documents).
     *
     * @private
     */
    _onDownload: function () {
        this.trigger_up('download', {
            resIds: this.records.map(record => record.res_id),
        });
    },
    /**
     * Opens a wizard to edit the record linked to the document.
     * @param {MouseEvent} ev
     */
    _onEditModel: function (ev) {
        this.trigger_up('edit_model', {
            document: this.records[0].data,
        });
    },
    /**
     * Intercept 'field_changed' events as they may concern several records, and
     * not one as the events suggest. Trigger a 'save_multi' event instead,
     * which will be handled by the DocumentsKanbanController.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onFieldChanged: async function (ev) {
        ev.stopPropagation();
        const fieldName = ev.target.name;
        if (
            ev.target.field.type === 'many2one' &&
            ev.data.changes[fieldName] &&
            !ev.data.changes[fieldName].id
        ) {
            this._registerWidget(ev.data.dataPointID, fieldName, ev.target);
            await StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
            const record = this.model.get(ev.data.dataPointID);
            ev.data.changes[fieldName].id = record.data[fieldName].res_id;
        }
        this._saveMulti(ev.data.changes);
    },
    /**
     * Lock the current attachment for the current user. This assumes that there
     * is only one selected attachment (the lock button is hidden when several
     * records are selected).
     *
     * @private
     */
    _onLock: function () {
        this.trigger_up('lock_attachment', {
            resId: this.records[0].res_id,
        });
    },
    /**
     * Apply a style-class to a sidebar action when its button is hover
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseoverRule: function (ev) {
        $(ev.currentTarget).closest('.o_inspector_trigger_hover_target').addClass('o_inspector_hover');
    },
    /**
     * Remove the style-class when the sidebar action button is not hover
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseoutRule: function (ev) {
        $(ev.currentTarget).closest('.o_inspector_trigger_hover_target').removeClass('o_inspector_hover');
    },
    /**
     * @private
     */
    _onOpenChatter: function () {
        this.trigger_up('open_chatter');
    },
    /**
     * Open the document previewer, a fullscreen preview of the image with
     * download and print options.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onOpenPreview: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.pendingSavingRequests > 0)
            return;
        const activeId = $(ev.currentTarget).data('id');
        if (activeId) {
            const records = this.records.map(record => record.data);
            this.trigger_up('kanban_image_clicked', {
                recordId: activeId,
                recordList: records
            });
        }
    },
    /**
     * Open the business object linked to the selected record in a form view.
     *
     * @private
     */
    _onOpenResource: function () {
        const record = this.records[0];
        this.trigger_up('open_record', {
            resId: record.data.res_id,
            resModel: record.data.res_model,
        });
    },
    /**
     * Remove the clicked tag from the selected records.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onRemoveTag: function (ev) {
        ev.stopPropagation();
        const tagId = $(ev.currentTarget).closest('.o_inspector_tag').data('id');
        const changes = {
            tag_ids: {
                operation: 'FORGET',
                resIds: [tagId],
            },
        };
        this._saveMulti(changes);
    },
    /**
     *
     * @private
     */
    _onReplace: function () {
        this.trigger_up('set_file', {
            id: this.records[0].data.id,
        });
    },
    /**
     * Share the selected documents
     *
     * @private
     */
    _onShare: function () {
        this.trigger_up('share_ids', {
            resIds: this.records.map(record => record.res_id),
        });
    },
    /**
     * Trigger a search or close the dropdown if it is already open when the
     * input is clicked.
     *
     * @private
     */
    _onTagInputClicked: function () {
        if (this.$tagInput.autocomplete("widget").is(":visible")) {
            this.$tagInput.autocomplete("close");
        } else {
            this.$tagInput.autocomplete('search');
        }
    },
    /**
     * Trigger a Workflow Rule's action on the selected records
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onTriggerRule: function (ev) {
        const $btn = $(ev.currentTarget);
        const ruleId = $btn.closest('.o_inspector_rule').data('id');
        $btn.prop('disabled', true);
        this.trigger_up('trigger_rule', {
            records: this.records,
            ruleId: ruleId
        });
    },
});

return DocumentsInspector;

});
