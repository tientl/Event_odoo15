odoo.define('documents.test_utils', function (require) {
"use strict";

const AbstractStorageService = require('web.AbstractStorageService');
const RamStorage = require('web.RamStorage');

const { start } = require('@mail/utils/test_utils');

async function createDocumentsView(params) {
    params.archs = params.archs || {};
    var searchArch = params.archs[`${params.model},false,search`] || '<search></search>';
    var searchPanelArch = `
        <searchpanel>
            <field name="folder_id" string="Workspace" enable_counters="1"/>
            <field name="tag_ids" select="multi" groupby="facet_id" enable_counters="1"/>
            <field name="res_model" select="multi" string="Attached To" enable_counters="1"/>
        </searchpanel>
    `;
    searchArch = searchArch.split('</search>')[0] + searchPanelArch + '</search>';
    params.archs[`${params.model},false,search`] = searchArch;
    if (!params.services || !params.services.local_storage) {
        // the searchPanel uses the localStorage to store/retrieve default
        // active category value
        params.services = params.services || {};
        const RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
        params.services.local_storage = RamStorageService;
    }

    const { widget } = await start(
        Object.assign({}, params, {
            hasView: true,
        })
    );
    return widget;
}

return {
    createDocumentsView,
};

});
