/** @odoo-module **/

import Domain from 'web.Domain';
import MockServer from 'web.MockServer';

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async _performRpc(route, args) {
        if (route.indexOf('/documents/image') >= 0 ||
            _.contains(['.png', '.jpg'], route.substr(route.length - 4))) {
            return Promise.resolve();
        }
        if (args.model === 'documents.share' && args.method === 'check_access_rights') {
            return true;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Mocks the '_get_models' method of the model 'documents.document'.
     *
     * @param {string} model
     * @param {any[]} domain
     */
    _mockGetModels(model, domain) {
        const notAFile = [];
        const notAttached = [];
        const models = [];
        const groups = this._mockReadGroup(model, {
            domain: domain,
            fields: ['res_model'],
            groupby: ['res_model'],
        });
        for (const group of groups) {
            if (!group.res_model) {
                notAFile.push({
                    id: group.res_model,
                    display_name: "Not a file",
                    __count: group.res_model_count,
                });
            } else if (group.res_model === 'documents.document') {
                notAttached.push({
                    id: group.res_model,
                    display_name: "Not attached",
                    __count: group.res_model_count,
                });
            } else {
                const { res_model_name } = this.data['documents.document'].records.find(
                    record => record.res_model === group.res_model
                );
                models.push({
                    id: group.res_model,
                    display_name: res_model_name,
                    __count: group.res_model_count,
                });
            }
        }
        const sorted = models.sort(({ display_name: a }, { display_name: b }) => {
            return a > b ? 1 : a < b ? -1 : 0;
        });
        return [...sorted, ...notAttached, ...notAFile];
    },
    /**
     * Override to handle the specific case of model 'documents.document'.
     *
     * @override
     */
    _mockSearchPanelSelectRange: function (model, [fieldName], kwargs) {
        if (model === 'documents.document' && fieldName === 'folder_id') {
            const enableCounters = kwargs.enable_counters || false;
            const fields = ['display_name', 'description', 'parent_folder_id'];
            const records = this._mockSearchRead('documents.folder', [[], fields], {});

            let domainImage = new Map();
            if (enableCounters) {
                const modelDomain = Domain.prototype.normalizeArray([
                    ...(kwargs.search_domain, []),
                    ...(kwargs.category_domain, []),
                    ...(kwargs.filter_domain, []),
                    [fieldName, '!=', false],
                ]);
                domainImage = this._mockSearchPanelDomainImage(model, fieldName, modelDomain, enableCounters);
            }

            const valuesRange = new Map();
            for (const record of records) {
                if (enableCounters) {
                    record.__count = domainImage.get(record.id) ? domainImage.get(record.id).__count : 0;
                }
                const value = record.parent_folder_id;
                record.parent_folder_id = value && value[0];
                valuesRange.set(record.id, record);
            }
            if (kwargs.enable_counters) {
                this._mockSearchPanelGlobalCounters(valuesRange, 'parent_folder_id');
            }
            return {
                parent_field: 'parent_folder_id',
                values: [...valuesRange.values()],
            };
        }
        return this._super(...arguments);
    },
    /**
     * Override to handle the specific case of model 'documents.document'.
     *
     * @override
     */
    _mockSearchPanelSelectMultiRange: function (model, [fieldName], kwargs) {
        const searchDomain = kwargs.search_domain || [];
        const categoryDomain = kwargs.category_domain || [];
        const filterDomain = kwargs.filter_domain || [];

        if (model === 'documents.document') {
            if (fieldName === 'tag_ids') {
                const folderId = categoryDomain.length ? categoryDomain[0][2] : false;
                if (folderId) {
                    const domain = Domain.prototype.normalizeArray([
                        ...searchDomain,
                        ...categoryDomain,
                        ...filterDomain,
                        [fieldName, '!=', false],
                    ]);
                    return {values: this.data['documents.tag'].get_tags(domain, folderId), };
                } else {
                    return {values: [], };
                }
            } else if (fieldName === 'res_model') {
                let domain = Domain.prototype.normalizeArray([...searchDomain, ...categoryDomain]);
                const modelValues = this._mockGetModels(model, domain);
                if (filterDomain) {
                    domain = Domain.prototype.normalizeArray([
                        ...searchDomain,
                        ...categoryDomain,
                        ...filterDomain,
                    ]);
                    const modelCount = {};
                    for (const { id, __count } of this._mockGetModels(model, domain)) {
                        modelCount[id] = __count;
                    }
                    modelValues.forEach(m => m.__count = modelCount[m.id] || 0);
                }
                return {values: modelValues, };
            }
        }
        return this._super(...arguments);
    },
});
