odoo.define('web_map.MapView', function (require) {
"use strict";

const MapModel = require('web_map.MapModel');
const MapController = require('web_map.MapController');
const MapRenderer = require('web_map.MapRenderer');
const AbstractView = require('web.AbstractView');
const RendererWrapper = require('web.RendererWrapper');
const utils = require('web.utils');
const viewRegistry = require('web.view_registry');
const _t = require('web.core')._t;

const MapView = AbstractView.extend({
    jsLibs: [
        '/web_map/static/lib/leaflet/leaflet.js',
    ],
    config: _.extend({}, AbstractView.prototype.config, {
        Model: MapModel,
        Controller: MapController,
        Renderer: MapRenderer,
    }),
    icon: 'fa-map-marker',
    display_name: 'Map',
    viewType: 'map',
    mobile_friendly: true,
    searchMenuTypes: ['filter', 'groupBy', 'favorite'],

    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        const fieldNames = [];
        const fieldNamesMarkerPopup = [];

        this.loadParams.resPartnerField = this.arch.attrs.res_partner;
        fieldNames.push(this.arch.attrs.res_partner);
        fieldNames.push('display_name');

        if (this.arch.attrs.default_order) {
            this.loadParams.orderBy = [{ name: this.arch.attrs.default_order || 'display_name', asc: true }];
        }

        const routing = ["true", "True", "1"].includes(this.arch.attrs.routing);

        this.loadParams.limit = this.arch.attrs.limit ?
            parseInt(this.arch.attrs.limit, 10) :
            params.limit || 80;
        this.loadParams.routing = routing;
        this.rendererParams.routing = routing;
        this.rendererParams.numbering = this.arch.attrs.routing ? true : false;
        this.rendererParams.defaultOrder = this.arch.attrs.default_order;
        this.rendererParams.panelTitle = this.arch.attrs.panel_title || params.displayName || _t('Items');
        this.rendererParams.hideTitle = utils.toBoolElse(this.arch.attrs.hide_title || '', false);

        const hideName = utils.toBoolElse(this.arch.attrs.hide_name || '', false);
        this.rendererParams.hideName = hideName;
        if (!hideName) {
            fieldNames.push('display_name');
        }
        this.rendererParams.hideAddress = utils.toBoolElse(this.arch.attrs.hide_address || '', false);

        this.arch.children.forEach(node => {
            if (node.tag === 'field') {
                fieldNames.push(node.attrs.name);
                fieldNamesMarkerPopup.push({ fieldName: node.attrs.name, string: node.attrs.string });
            }
        });
        this.loadParams.fieldsInfo = this.fields;
        this.loadParams.fieldNames = _.uniq(fieldNames);
        this.rendererParams.fieldNamesMarkerPopup = fieldNamesMarkerPopup;

        this.rendererParams.hasFormView = params.actionViews.some(view => view.type === "form");

        this.controllerParams.actionName = params.action ? params.action.name : _t("Untitled");
    },
    /**
     * @override
     */
    getRenderer(parent, state) {
        state = Object.assign({}, state, this.rendererParams);
        return new RendererWrapper(null, this.config.Renderer, state);
    },
});

viewRegistry.add('map', MapView);

return MapView;
});
