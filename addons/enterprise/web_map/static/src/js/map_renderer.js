/* global L */
// L is the object of leaflet
odoo.define('web_map.MapRenderer', function (require) {
    "use strict";

    const AbstractRendererOwl = require('web.AbstractRendererOwl');
    const { format } = require("web.field_utils");

    const { useRef, useState } = owl.hooks;

    const apiTilesRouteWithToken =
        'https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}';
    const apiTilesRouteWithoutToken = 'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png';

    const colors = [
        '#F06050',
        '#6CC1ED',
        '#F7CD1F',
        '#814968',
        '#30C381',
        '#D6145F',
        '#475577',
        '#F4A460',
        '#EB7E7F',
        '#2C8397',
    ];

    const mapTileAttribution = `
        © <a href="https://www.mapbox.com/about/maps/">Mapbox</a>
        © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>
        <strong>
            <a href="https://www.mapbox.com/map-feedback/" target="_blank">
                Improve this map
            </a>
        </strong>`;

    class MapRenderer extends AbstractRendererOwl {
        /**
         * @constructor
         */
        constructor() {
            super(...arguments);
            this.leafletMap = null;
            this.markers = [];
            this.polylines = [];
            this.mapContainerRef = useRef('mapContainer');
            this.state = useState({
                closedGroupIds: [],
            });
        }
        /**
         * Load marker icons.
         *
         * @override
         */
        async willStart() {
            const p = { method: 'GET' };
            [this._pinCircleSVG, this._pinNoCircleSVG] = await Promise.all([
                this.env.services.httpRequest('web_map/static/img/pin-circle.svg', p, 'text'),
                this.env.services.httpRequest('web_map/static/img/pin-no-circle.svg', p, 'text'),
            ]);
            return super.willStart(...arguments);
        }
        /**
         * Initialize and mount map.
         *
         * @override
         */
        mounted() {
            this.leafletMap = L.map(this.mapContainerRef.el, {
                maxBounds: [L.latLng(180, -180), L.latLng(-180, 180)],
            });
            L.tileLayer(this.apiTilesRoute, {
                attribution: mapTileAttribution,
                tileSize: 512,
                zoomOffset: -1,
                minZoom: 2,
                maxZoom: 19,
                id: 'mapbox/streets-v11',
                accessToken: this.props.mapBoxToken,
            }).addTo(this.leafletMap);
            this._updateMap();
            super.mounted(...arguments);
        }
        /**
         * Update position in the map, markers and routes.
         *
         * @override
         */
        patched() {
            this._updateMap();
            super.patched(...arguments);
        }
        /**
         * Update group opened/closed state.
         *
         * @override
         */
        willUpdateProps(nextProps) {
            if (this.props.groupBy !== nextProps.groupBy) {
                this.state.closedGroupIds = [];
            }
            return super.willUpdateProps(...arguments);
        }
        /**
         * Remove map and the listeners on its markers and routes.
         *
         * @override
         */
        willUnmount() {
            for (const marker of this.markers) {
                marker.off('click');
            }
            for (const polyline of this.polylines) {
                polyline.off('click');
            }
            this.leafletMap.remove();
            super.willUnmount(...arguments);
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * Return the route to the tiles api with or without access token.
         *
         * @returns {string}
         */
        get apiTilesRoute() {
            return this.props.mapBoxToken ? apiTilesRouteWithToken : apiTilesRouteWithoutToken;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * If there's located records, adds the corresponding marker on the map.
         * Binds events to the created markers.
         *
         * @private
         */
        _addMarkers() {
            this._removeMarkers();

            const markersInfo = {};
            let records = this.props.records;
            if (this.props.groupBy) {
                records = Object.entries(this.props.recordGroups)
                    .filter(([key]) => !this.state.closedGroupIds.includes(key))
                    .flatMap(([, value]) => value.records);
            }

            for (const record of records) {
                const partner = record.partner;
                if (partner && partner.partner_latitude && partner.partner_longitude) {
                    const key = `${partner.partner_latitude}-${partner.partner_longitude}`;
                    if (key in markersInfo) {
                        markersInfo[key].record = record;
                        markersInfo[key].ids.push(record.id);
                    } else {
                        markersInfo[key] = { record: record, ids: [record.id] };
                    }
                }
            }

            for (const markerInfo of Object.values(markersInfo)) {
                const params = {
                    count: markerInfo.ids.length,
                    isMulti: markerInfo.ids.length > 1,
                    number: this.props.records.indexOf(markerInfo.record) + 1,
                    numbering: this.props.numbering,
                    pinSVG: (this.props.numbering ? this._pinNoCircleSVG : this._pinCircleSVG),
                };

                if (this.props.groupBy) {
                    const group = Object.entries(this.props.recordGroups)
                        .find(([, value]) => value.records.includes(markerInfo.record));
                    params.color = this._getGroupColor(group[0]);
                    params.number = group[1].records.indexOf(markerInfo.record) + 1;
                }

                // Icon creation
                const iconInfo = {
                    className: 'o_map_marker',
                    html: this.env.qweb.renderToString('web_map.marker', params),
                };

                // Attach marker with icon and popup
                const marker = L.marker([
                    markerInfo.record.partner.partner_latitude,
                    markerInfo.record.partner.partner_longitude
                ], { icon: L.divIcon(iconInfo) });
                marker.addTo(this.leafletMap);
                marker.on('click', () => {
                    this._createMarkerPopup(markerInfo);
                });
                this.markers.push(marker);
            }
        }
        /**
         * If there are computed routes, create polylines and add them to the map.
         * each element of this.props.routeInfo[0].legs array represent the route between
         * two waypoints thus each of these must be a polyline.
         *
         * @private
         */
        _addRoutes() {
            this._removeRoutes();
            if (!this.props.mapBoxToken || !this.props.routeInfo.routes.length) {
                return;
            }

            for (const leg of this.props.routeInfo.routes[0].legs) {
                const latLngs = [];
                for (const step of leg.steps) {
                    for (const coordinate of step.geometry.coordinates) {
                        latLngs.push(L.latLng(coordinate[1], coordinate[0]));
                    }
                }

                const polyline = L.polyline(latLngs, {
                    color: 'blue',
                    weight: 5,
                    opacity: 0.3,
                }).addTo(this.leafletMap);

                const polylines = this.polylines;
                polyline.on('click', function () {
                    for (const polyline of polylines) {
                        polyline.setStyle({ color: 'blue', opacity: 0.3 });
                    }
                    this.setStyle({ color: 'darkblue', opacity: 1.0 });
                });
                this.polylines.push(polyline);
            }
        }
        /**
         * Create a popup for the specified marker.
         *
         * @private
         * @param {Object} markerInfo
         */
        _createMarkerPopup(markerInfo) {
            const popupFields = this._getMarkerPopupFields(markerInfo);
            const partner = markerInfo.record.partner;
            const popupHtml = this.env.qweb.renderToString('web_map.markerPopup', {
                fields: popupFields,
                hasFormView: this.props.hasFormView,
                url: `https://www.google.com/maps/dir/?api=1&destination=${partner.partner_latitude},${partner.partner_longitude}`,
            });

            const popup = L.popup({ offset: [0, -30] })
                .setLatLng([partner.partner_latitude, partner.partner_longitude])
                .setContent(popupHtml)
                .openOn(this.leafletMap);

            const openBtn = popup.getElement().querySelector('button.o_open');
            if (openBtn) {
                openBtn.onclick = () => {
                    this.trigger('open_clicked', { ids: markerInfo.ids });
                };
            }
            return popup;
        }
        /**
         * @private
         * @param {Number} groupId
         */
        _getGroupColor(groupId) {
            const index = Object.keys(this.props.recordGroups).indexOf(groupId);
            return colors[index % colors.length];
        }
        /**
         * Creates an array of latLng objects if there is located records.
         *
         * @private
         * @returns {latLngBounds|boolean} objects containing the coordinates that
         *          allows all the records to be shown on the map or returns false
         *          if the records does not contain any located record.
         */
        _getLatLng() {
            const tabLatLng = [];
            for (const record of this.props.records) {
                const partner = record.partner;
                if (partner && partner.partner_latitude && partner.partner_longitude) {
                    tabLatLng.push(L.latLng(partner.partner_latitude, partner.partner_longitude));
                }
            }
            if (!tabLatLng.length) {
                return false;
            }
            return L.latLngBounds(tabLatLng);
        }
        /**
         * Get the fields' name and value to display in the popup.
         *
         * @private
         * @param {Object} markerInfo
         * @returns {Object} value contains the value of the field and string
         *                   contains the value of the xml's string attribute
         */
        _getMarkerPopupFields(markerInfo) {
            const record = markerInfo.record;
            const fieldsView = [];
            // Only display address in multi coordinates marker popup
            if (markerInfo.ids.length > 1) {
                if (!this.props.hideAddress) {
                    fieldsView.push({
                        value: record.partner.contact_address_complete,
                        string: this.env._t("Address"),
                    });
                }
                return fieldsView;
            }
            if (!this.props.hideName) {
                fieldsView.push({
                    value: record.display_name,
                    string: this.env._t("Name"),
                });
            }
            if (!this.props.hideAddress) {
                fieldsView.push({
                    value: record.partner.contact_address_complete,
                    string: this.env._t("Address"),
                });
            }
            for (const field of this.props.fieldNamesMarkerPopup) {
                if (record[field.fieldName]) {
                    let fieldName = record[field.fieldName] instanceof Array ?
                        record[field.fieldName][1] :
                        record[field.fieldName];

                    if (["date", "datetime"].includes(field.type)) {
                        const date = moment.utc(fieldName);
                        fieldName = format[field.type](date);
                    }

                    fieldsView.push({
                        value: fieldName,
                        string: field.string,
                    });
                }
            }
            return fieldsView;
        }
        /**
         * Remove the markers from the map and empty the markers array.
         *
         * @private
         */
        _removeMarkers() {
            for (const marker of this.markers) {
                this.leafletMap.removeLayer(marker);
            }
            this.markers = [];
        }
        /**
         * Remove the routes from the map and empty the the polyline array.
         *
         * @private
         */
        _removeRoutes() {
            for (const polyline of this.polylines) {
                this.leafletMap.removeLayer(polyline);
            }
            this.polylines = [];
        }
        /**
         * Update position in the map, markers and routes.
         *
         * @private
         */
        _updateMap() {
            if (this.props.shouldUpdatePosition) {
                const initialCoord = this._getLatLng();
                if (initialCoord) {
                    this.leafletMap.flyToBounds(initialCoord, { animate: false });
                } else {
                    this.leafletMap.fitWorld();
                }
                this.leafletMap.closePopup();
            }
            this._addMarkers();
            this._addRoutes();
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Center the map on a certain pin and open the popup linked to it.
         *
         * @private
         * @param {Object} record
         */
        _centerAndOpenPin(record) {
            const popup = this._createMarkerPopup({
                record: record,
                ids: [record.id],
            });
            const px = this.leafletMap.project([record.partner.partner_latitude, record.partner.partner_longitude]);
            const popupHeight = popup.getElement().offsetHeight;
            px.y -= popupHeight / 2;
            const latlng = this.leafletMap.unproject(px);
            this.leafletMap.panTo(latlng, { animate: true });
        }
        /**
         * @private
         * @param {Number} id
         */
        _toggleGroup(id) {
            if (this.state.closedGroupIds.includes(id)) {
                const index = this.state.closedGroupIds.indexOf(id);
                this.state.closedGroupIds.splice(index, 1);
            } else {
                this.state.closedGroupIds.push(id);
            }
        }
    }
    MapRenderer.props = {
        arch: Object,
        count: Number,
        defaultOrder: {
            type: String,
            optional: true,
        },
        fetchingCoordinates: Boolean,
        fieldNamesMarkerPopup: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    fieldName: String,
                    string: String,
                    type: String,
                },
            },
        },
        groupBy: [String, Boolean],
        hasFormView: Boolean,
        hideAddress: Boolean,
        hideName: Boolean,
        isEmbedded: Boolean,
        limit: Number,
        mapBoxToken: { type: [Boolean, String], optional: 1 },
        noContentHelp: {
            type: String,
            optional: true,
        },
        numbering: Boolean,
        hideTitle: Boolean,
        panelTitle: String,
        offset: Number,
        partners: { type: [Array, Boolean], optional: 1 },
        recordGroups: Object,
        records: Array,
        routeInfo: {
            type: Object,
            optional: true,
        },
        routing: Boolean,
        routingError: {
            type: String,
            optional: true,
        },
        shouldUpdatePosition: Boolean,
    };
    MapRenderer.template = 'web_map.MapRenderer';

    return MapRenderer;
});
