odoo.define('documents.modelMixin', function (require) {
'use strict';

const DocumentsModelMixin = {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Integer} recordId
     * @returns {Promise}
     */
    async fetchActivities(recordId) {
        const record = this.localData[recordId];
        record.specialData.activity_ids = await this._fetchSpecialActivity(record, 'activity_ids');
    },
    /**
     * Adds complementary data to the model.
     */
    get(dataPointId) {
        const result = this._super(...arguments);
        if (result && result.type === 'list') {
            const dataPoint = this.localData[dataPointId];
            result.size = dataPoint.size;
        }
        return result;
    },
    /**
     * Override to explicitly specify the 'searchDomain', which is the domain
     * coming from the search view. This domain is used to load the related
     * models, whereas a combination of this domain and the domain of the
     * DocumentsSelector is used for the classical search_read.
     *
     * Also fetch the folders here, so that it is done only once, as it doesn't
     * depend on the domain. Moreover, the folders are necessary to fetch the
     * tags, as we first fetch tags of the default folder.
     *
     * @override
     */
    async load(params) {
        const prom = this._super(...arguments);
        const dataPointId = await this._fetchAdditionalData(prom, params);
        this._currentRootDataPointId = dataPointId;
        return dataPointId;
    },
    /**
     * Override to handle the 'selectorDomain' coming from the
     * DocumentsInspector, and to explicitely specify the 'searchDomain', which
     * is the domain coming from the search view. This domain is used to load
     * the related models, whereas a combination of the 'searchDomain' and the
     * 'selectorDomain' is used for the classical search_read.
     *
     * @override
     * @param {Array[]} [options.selectorDomain] the domain coming from the
     *   DocumentsInspector
     */
    reload(id, options) {
        const prom = this._super(...arguments);
        if (this._currentRootDataPointId === id) {
            return this._fetchAdditionalData(prom, options);
        } else {
            return prom;
        }
    },
    /**
     * Save changes on several records in a mutex, and reload.
     *
     * @param {string[]} recordIds
     * @param {Object} values
     * @param {string} parentId
     * @returns {Promise<string>} resolves with the parentId
     */
    saveMulti(recordIds, values, parentId) {
        return this.mutex.exec(() => this._saveMulti(recordIds, values, parentId));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch additional data required by the DocumentsList view.
     *
     * @private
     * @param {Promise<string>} prom resolves with the id of the dataPoint
     *   created by the load/reload call
     * @param {Object} params parameters/options passed to the load/reload function
     * @returns {Promise<string>} resolves with the dataPointId
     */
    async _fetchAdditionalData(prom, params) {
        const proms = [prom];
        proms.push(this._fetchSize(params));
        const results = await Promise.all(proms);
        const dataPointId = results[0];
        const size = results[1];
        const dataPoint = this.localData[dataPointId];
        dataPoint.size = size;
        return dataPointId;
    },
    /**
     * Fetch the sum of the size of the documents matching the current domain.
     *
     * @private
     * @param {Object} [param0]
     * @param {Array} domain
     */
    async _fetchSize({ domain }={}) {
        const result = await this._rpc({
            model: 'documents.document',
            method: 'read_group',
            domain: domain || [],
            fields: ['file_size'],
            groupBy: [],
        });
        const size = result[0].file_size / (1000 * 1000); // in MB
        return Math.round(size * 100) / 100;

    },
    /**
     * Save changes on several records. Be careful that this function doesn't
     * handle all field types: only primitive types, many2ones and many2manys
     * (forget and link_to commands) are covered.
     *
     * @private
     * @param {string[]} recordIds
     * @param {Object} values
     * @param {string} parentId
     * @returns {Promise<string>} resolves with the parentId
     */
    _saveMulti(recordIds, values, parentId) {
        const parent = this.localData[parentId];
        const resIds = recordIds.map(recordId => this.localData[recordId].res_id);
        const changes = _.mapObject(values, (value, fieldName) => {
            const field = parent.fields[fieldName];
            if (field.type === 'many2one') {
                value = value.id || false;
            } else if (field.type === 'many2many') {
                const command = value.operation === 'FORGET' ? 3 : 4;
                value = value.resIds.map(resId => [command, resId]);
            }
            return value;
        });

        return this._rpc({
            model: parent.model,
            method: 'write',
            args: [resIds, changes],
        });
    },
};

return DocumentsModelMixin;

});
