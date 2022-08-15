odoo.define('web_map.view_view_tests', function (require) {
"use strict";

const MapView = require('web_map.MapView');
const MapModel = require('web_map.MapModel');
const testUtils = require('web.test_utils');

const { toggleGroupByMenu, toggleMenuItem } = require("@web/../tests/search/helpers");
const createView = testUtils.createAsyncView;
const patchDate = testUtils.mock.patchDate;

QUnit.module('mapView', {
    beforeEach: function () {
        this.data = {
            'project.task': {
                fields: {
                    display_name: { string: "name", type: "char" },
                    scheduled_date: { string: "Schedule date", type: "datetime"},
                    sequence: { string: "sequence", type: 'integer' },
                    partner_id: { string: "partner", type: "many2one", relation: 'res.partner' },
                    another_partner_id: { string: "another relation", type: "many2one", relation: 'res.partner}' },
                    user_ids: {string: "assignees", type:"many2many", relation: 'res.users'}
                },
                records: [
                    { id: 1, display_name: "project", partner_id: 1 }
                ],
                oneRecord: {
                    records: [
                        { id: 1, display_name: "Foo", partner_id: [1] }
                    ],
                    length: 1
                },

                oneRecordFieldDateTime: {
                    records: [
                        { id: 1, display_name: "Foo", scheduled_date: "02/07/2022 21:09:31", partner_id: [1] }
                    ],
                    length: 1
                },


                twoRecords: {
                    records: [
                        { id: 1, display_name: "FooProject", sequence: 1, partner_id: [1], user_ids: [1] },
                        { id: 2, display_name: 'BarProject', sequence: 2, partner_id: [2], user_ids: [1, 2] },
                    ],
                    length: 2
                },

                threeRecords: {
                    records: [
                        { id: 1, display_name: "FooProject", sequence: 1, partner_id: [1] },
                        { id: 2, display_name: 'BarProject', sequence: 2, partner_id: [2] },
                        { id: 1, display_name: "FooBarProject", sequence: 3, partner_id: [1] }
                    ],
                    length: 3
                },

                twoRecordOnePartner: {
                    records: [
                        { id: 1, display_name: "FooProject", partner_id: [1] },
                        { id: 2, display_name: 'BarProject', partner_id: [1] },
                    ],
                    length: 2
                },
                noRecord: {
                    records: [],
                    length: 0
                },
                recordWithouthPartner: {
                    records: [
                        { id: 1, display_name: "Foo", partner_id: [] }
                    ],
                    length: 1
                },
                anotherPartnerId: {
                    records: [
                        { id: 1, display_name: "FooProject", another_partner_id: [1] },
                    ],
                    length: 1
                }
            },

            'res.partner': {
                fields: {
                    name: { string: "Customer", type: "char" },
                    'partner_latitude': { string: "Latitude", type: "float" },
                    'partner_longitude': { string: "Longitude", type: "float" },
                    'contact_address_complete': { string: 'Address', type: "char" },
                    'task_ids': {
                        string: 'Task',
                        type: "one2many",
                        relation: "project.task",
                        relation_field: "partner_id"
                    },
                    sequence: { string: 'sequence', type: 'integer' }
                },
                records: [
                    {
                        id: 1, name: 'Foo', 'partner_latitude': 10.0, 'partner_longitude': 10.5,
                        'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 1
                    },
                    {
                        id: 2, name: 'Foo', 'partner_latitude': 10.0, 'partner_longitude': 10.5,
                        'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 3
                    },
                    {
                        id: 3, name: 'Bar', 'partner_latitude': 11.0, 'partner_longitude': 11.5,
                        'contact_address_complete': 'Chaussée de Wavre 50, 1367, Ramillies', sequence: 4
                    },

                ],
                coordinatesNoAddress: [
                    {
                        id: 1, name: 'Foo', 'partner_latitude': 10.0, 'partner_longitude': 10.5
                    }
                ],
                oneLocatedRecord: [
                    {
                        id: 1, name: 'Foo', 'partner_latitude': 10.0, 'partner_longitude': 10.5,
                        'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 1
                    },
                ],
                wrongCoordinatesNoAddress: [
                    {
                        id: 1, name: 'Foo', 'partner_latitude': 10000.0, 'partner_longitude': 100000.5
                    }
                ],
                noCoordinatesGoodAddress: [
                    {
                        id: 1, name: 'Foo', 'partner_latitude': 0, 'partner_longitude': 0,
                        'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies'
                    }
                ],
                emptyRecords: [],
                twoRecordsAddressNoCoordinates:
                    [
                        {
                            id: 2, name: 'Foo',
                            'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 3
                        },
                        {
                            id: 1, name: 'Bar',
                            'contact_address_complete': 'Chaussée de Louvain 94, 5310 Éghezée', sequence: 1
                        },
                    ],
                twoRecordsAddressCoordinates:
                    [
                        {
                            id: 2, name: 'Foo', 'partner_latitude': 10.0, 'partner_longitude': 10.5,
                            'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 3
                        },
                        {
                            id: 1, name: 'Bar', 'partner_latitude': 10.0, 'partner_longitude': 10.5,
                            'contact_address_complete': 'Chaussée de Louvain 94, 5310 Éghezée', sequence: 1
                        },
                    ],
                twoRecordsOneUnlocated:
                    [
                        {
                            id: 1, name: 'Foo',
                            'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 3
                        },
                        {
                            id: 2, name: 'Bar',
                        },
                    ],
                unlocatedRecords:
                    [
                        { id: 1, name: 'Foo' },
                    ],
                noCoordinatesWrongAddress:
                    [
                        {
                            id: 1, name: 'Foo',
                            'contact_address_complete': 'Cfezfezfefes'
                        }
                    ],
            },

            'res.users': {
                fields: {
                    name: { string: 'User', type: 'char' },
                    sequence: { string: 'sequence', type: 'integer' }
                },
                twoRecords: {
                    records: [
                        { id: 1, name: 'Au', sequence: 1 },
                        { id: 2, name: 'On', sequence: 2 },
                        ],
                    length: 2
                },
            },
        };
        testUtils.mock.patch(MapModel, {
            // set delay to 0 as _fetchCoordinatesFromAddressOSM is mocked
            COORDINATE_FETCH_DELAY: 0,
            _fetchCoordinatesFromAddressMB: function (record) {
                if (this.data.mapBoxToken !== 'token') {
                    return Promise.reject({ status: 401 });
                }
                const coordinates = [];
                coordinates[0] = 10.0;
                coordinates[1] = 10.5;
                const geometry = { coordinates };
                const features = [];
                features[0] = { geometry };
                const successResponse = { features };
                const failResponse = { features: [] };
                switch (record.contact_address_complete) {
                    case 'Cfezfezfefes':
                        return Promise.resolve(failResponse);
                    case '':
                        return Promise.resolve(failResponse);
                }
                return Promise.resolve(successResponse);
            },

            _fetchCoordinatesFromAddressOSM: function (record) {
                const coordinates = [];
                coordinates[0] = { lat: 10.0, lon: 10.5 };
                switch (record.contact_address_complete) {
                    case 'Cfezfezfefes':
                        return Promise.resolve([]);
                    case '':
                        return Promise.resolve([]);
                }
                return Promise.resolve(coordinates);
            },

            _fetchRoute: function () {
                if (this.data.mapBoxToken !== 'token') {
                    return Promise.reject({ status: 401 });
                }
                const legs = [];
                for (let i = 1; i < this.data.records.length; i++) {
                    const coordinates = [];
                    coordinates[0] = [10, 10.5];
                    coordinates[1] = [10, 10.6];
                    const geometry = { coordinates };
                    const steps = [];
                    steps[0] = { geometry };
                    legs.push({ steps: steps });
                }
                const routes = [];
                routes[0] = { legs };
                return Promise.resolve({ routes });
            },
            _notifyFetchedCoordinate: function () {
                // do not notify in tests as coords fetching is " synchronous "
            },
            _openStreetMapAPI: function () {
                // return promise to wait for it
                return this._openStreetMapAPIAsync();
            },
        });
    },
    afterEach: function () {
        testUtils.mock.unpatch(MapModel);
    }
}, function () {

    //--------------------------------------------------------------------------
    // Testing data fetching
    //--------------------------------------------------------------------------

    /**
     * data: no record
     * should display a map with the minimum level of zoom
     * Should have no record
     * Should have no marker
     * Should have no route
     */
    QUnit.test('Create a view with no record', async function (assert) {
        assert.expect(8);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch:
                `<map res_partner="partner_id" routing="true">
                    <field name="name" string="Project"/>
                </map>`,
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        assert.strictEqual(args.model, 'project.task',
                            'The model should be project.task');
                        assert.strictEqual(args.fields[0], 'partner_id');
                        assert.strictEqual(args.fields[1], 'display_name');
                        return Promise.resolve(this.data['project.task'].noRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        assert.ok(false,
                            'Should not search_read the partners if there are no partner');
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.model.resPartnerField, 'partner_id',
            'the resPartnerField should be set');

        assert.strictEqual(map.renderer.props.records.length, 0,
            'There should be no records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'No marker should be on a the map.');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'No route should be shown');
        assert.strictEqual(map.renderer.componentRef.comp.leafletMap.getZoom(), 2,
            'The map should at its minimum zoom level(2)');
        map.destroy();
    });

    /**
     * data: one record that has no partner linked to it
     * The record should be kept and displayed in the list of records in gray (no clickable)
     * should have no marker
     * Should have no route
     * Map should be at his minimum zoom level
     */
    QUnit.test('Create a view with one record that has no partner', async function (assert) {
        assert.expect(6);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].recordWithouthPartner);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].emptyRecords);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be no records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'No marker should be on a the map.');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'No route should be shown');
        assert.strictEqual(map.renderer.componentRef.comp.leafletMap.getZoom(), 2,
            'The map should at its minimum level of zoom(2)');
        assert.containsOnce(map, '.o_pin_list_container .o_pin_list_details li');
        assert.containsOnce(map, '.o_pin_list_container .o_pin_list_details li span');

        map.destroy();
    });

    /**
     * data: one record that has a partner which has coordinates but no address
     * One record
     * One marker
     * no route
     * Map should not be at his minimum zoom level
     *
     */
    QUnit.test('Create a view with one record and a partner located by coordinates', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].coordinatesNoAddress);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsOnce(map, 'div.leaflet-marker-icon',
            'There should be one marker on the map');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');

        map.destroy();
    });

    /**
     * data: one record linked to one partner with no address and wrong coordinates
     * api: MapBox
     * record should be kept and displayed in the list
     * no route
     * no marker
     * map should be at its minimum zoom level
     */
    QUnit.test('Create view with one record linked to a partner with wrong coordinates with MB', async function (assert) {
        assert.expect(5);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].wrongCoordinatesNoAddress);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 1, 'There should be one records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'There should be np marker on the map');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');
        assert.containsOnce(map, '.o_pin_list_container .o_pin_list_details li');
        assert.containsOnce(map, '.o_pin_list_container .o_pin_list_details li span');

        map.destroy();
    });

    /**
     * data: one record linked to one partner with no address and wrong coordinates
     * api: OpenStreet Map
     * record should be kept
     * no route
     * no marker
     * map should be at its minimum zoom level
     */
    QUnit.test('Create view with one record linked to a partner with wrong coordinates with OSM', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].wrongCoordinatesNoAddress);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 1, 'There should be one records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'There should be no marker on the map');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');

        map.destroy();
    });
    /**
     * data: one record linked to one partner with no coordinates and good address
     * api: OpenStreet Map
     * caching RPC called, assert good args
     * one record
     * no route
     */
    QUnit.test('Create View with one record linked to a partner with no coordinates and right address OSM', async function (assert) {
        assert.expect(7);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].noCoordinatesGoodAddress);
                    case '/web/dataset/call_kw/res.partner/update_latitude_longitude':
                        assert.strictEqual(args.model, "res.partner",
                            'The model should be "res.partner"');
                        assert.strictEqual(args.method, "update_latitude_longitude");
                        assert.strictEqual(args.args[0].length, 1,
                            'There should be one record needing caching');
                        assert.strictEqual(args.args[0][0].id, 1,
                            'The records\'s id should be 1');
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsOnce(map, 'div.leaflet-marker-icon',
            'There should be one marker on the map');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');

        map.destroy();
    });

    /**
     * data: one record linked to one partner with no coordinates and good address
     * api: MapBox
     * caching RPC called, assert good args
     * one record
     * no route
     */
    QUnit.test('Create View with one record linked to a partner with no coordinates and right address MB', async function (assert) {
        assert.expect(7);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].noCoordinatesGoodAddress);
                    case '/web/dataset/call_kw/res.partner/update_latitude_longitude':
                        assert.strictEqual(args.model, "res.partner",
                            'The model should be "res.partner"');
                        assert.strictEqual(args.method, "update_latitude_longitude");
                        assert.strictEqual(args.args[0].length, 1,
                            'There should be one record needing caching');
                        assert.strictEqual(args.args[0][0].id, 1,
                            'The records\'s id should be 1');
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsOnce(map, 'div.leaflet-marker-icon',
            'There should be one marker on the map');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');

        map.destroy();
    });

    /**
     * data: one record linked to a partner with no coordinates and no address
     * api: MapBox
     * 1 record
     * no route
     * no marker
     * min level of zoom
     */
    QUnit.test('Create view with no located record', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].unlocatedRecords);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            }
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'No marker should be on a the map.');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'No route should be shown');
        assert.strictEqual(map.renderer.componentRef.comp.leafletMap.getZoom(), 2,
            'The map should at its minimum zoom level(2)');

        map.destroy();
    });

    /**
     * data: one record linked to a partner with no coordinates and no address
     * api: OSM
     * one record
     * no route
     * no marker
     * min level of zoom
     */
    QUnit.test('Create view with no located record OSM', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].unlocatedRecords);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            }
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'No marker should be on a the map.');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'No route should be shown');
        assert.strictEqual(map.renderer.componentRef.comp.leafletMap.getZoom(), 2,
            'The map should at its minimum zoom level(2)');

        map.destroy();
    });

    /**
     * data: one record linked to a partner with no coordinates and wrong address
     * api: OSM
     * one record
     * no route
     * no marker
     * min level zoom
     */
    QUnit.test('Create view with no badly located record OSM', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].noCoordinatesWrongAddress);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            }
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'No marker should be on a the map.');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'No route should be shown');
        assert.strictEqual(map.renderer.componentRef.comp.leafletMap.getZoom(), 2,
            'The map should at its minimum zoom level(2)');

        map.destroy();
    });

    /**
     * data: one record linked to a partner with no coordinates and wrong address
     * api: mapbox
     * one record
     * no route
     * no marker
     * min level zoom
     */

    QUnit.test('Create view with no badly located record MB', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].noCoordinatesWrongAddress);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            }
        });
        assert.strictEqual(map.renderer.props.records.length, 1,
            'There should be one records');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'No marker should be on a the map.');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'No route should be shown');
        assert.strictEqual(map.renderer.componentRef.comp.leafletMap.getZoom(), 2,
            'The map should at its minimum zoom level(2)');

        map.destroy();
    });

    /**
     * data: 2 records linked to the same partner
     * 2 records
     * 2 markers
     * no route
     * same partner object
     * 1 caching request
     */
    QUnit.test('Create a view with two located records same partner', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecordOnePartner);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 2,
            'There should be no records');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');
        assert.containsOnce(map.$('.leaflet-overlay-pane'), 'path',
            'There should be one route showing');
        assert.equal(map.renderer.props.records[0].partner, map.renderer.props.records[1].partner,
            'The records should have the same partner object as a property');

        map.destroy();
    });

    /**
     * data: 2 records linked to differnet partners
     * 2 records
     * 1 route
     * different partner object.
     * 2 caching
     */
    QUnit.test('Create a a view with two located records different partner', async function (assert) {
        assert.expect(5);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                    case '/web/dataset/call_kw/res.partner/update_latitude_longitude':
                        assert.strictEqual(args.args[0].length, 2,
                            'Should have 2 record needing caching');
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 2,
            'There should be no records');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');
        assert.containsOnce(map.$('.leaflet-overlay-pane'), 'path',
            'There should be one route showing');
        assert.notEqual(map.renderer.props.records[0].partner, map.renderer.props.records[1].partner,
            'The records should have the same partner object as a property');

        map.destroy();
    });

    /**
     * data: 2 valid res.partner records
     * test the case where the model is res.partner and the "res.partner" field is the id
     * should have 2 records,
     * 2 markers
     * no route
     */
    QUnit.test('Create a view with res.partner', async function (assert) {
        assert.expect(8);

        this.data['res.partner'].recordsPrimary = {
            records: [
                {
                    id: 2, name: 'Foo',
                    'contact_address_complete': 'Chaussée de Namur 40, 1367, Ramillies', sequence: 3
                },
                {
                    id: 1, name: 'FooBar',
                    'contact_address_complete': 'Chaussée de Louvain 94, 5310 Éghezée', sequence: 1
                }
            ], length: 2
        };
        const map = await createView({
            View: MapView,
            model: 'res.partner',
            data: this.data,
            arch: '<map res_partner="id"></map>',
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        assert.strictEqual(args.model, 'res.partner',
                            'The model should be res.partner');
                        assert.strictEqual(args.fields[0], 'id');
                        return Promise.resolve(this.data['res.partner'].recordsPrimary);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        assert.strictEqual(args.model, 'res.partner',
                            'The model should be res.partner as well');
                        assert.strictEqual(args.kwargs.domain[1][2][0], 2);
                        assert.strictEqual(args.kwargs.domain[1][2][1], 1);
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 2,
            'There should be two records');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route showing');

        map.destroy();
    });

    /**
     * data: 3 records linked to one located partner and one unlocated
     * test if only the 2 located records are displayed
     */
    QUnit.test('Create a view with 2 located records and 1 unlocated', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].threeRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsOneUnlocated);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.records.length, 3);
        assert.strictEqual(map.renderer.props.records[0].partner.id, 1,
            "The partner's id should be 1");
        assert.strictEqual(map.renderer.props.records[1].partner.id, 2,
            "The partner's id should be 2");
        assert.strictEqual(map.renderer.props.records[2].partner.id, 1,
            "The partner's id should be 1");

        map.destroy();
    });

    QUnit.test('Change load limit', async function (assert) {
        assert.expect(2);

        this.data['project.task'].records = this.data['project.task'].threeRecords.records;
        this.data['res.partner'].records = this.data['res.partner'].twoRecordsAddressCoordinates;
        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" limit="2"/>',
            session: {
                map_box_token: 'token'
            },
        });

        assert.strictEqual(testUtils.controlPanel.getPagerValue(map), '1-2');
        assert.strictEqual(testUtils.controlPanel.getPagerSize(map), '3');

        map.destroy();
    });

    //--------------------------------------------------------------------------
    // Renderer testing
    //--------------------------------------------------------------------------

    QUnit.test('Google Maps redirection', async function (assert) {
        assert.expect(2);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.$('a.btn.btn-primary').attr('href'),
            'https://www.google.com/maps/dir/?api=1&waypoints=10.5,10',
            'The link\'s URL should contain the right sets of coordinates');

        await testUtils.dom.click(map.$('.leaflet-marker-icon'));
        assert.strictEqual(map.$('div.leaflet-popup').find('a.btn.btn-primary').attr('href'),
            'https://www.google.com/maps/dir/?api=1&destination=10.5,10',
            'The link\'s URL should the right set of coordinates');

        map.destroy();
    });

    QUnit.test('Unicity of coordinates in Google Maps url', async function(assert){
        assert.expect(2);
        var map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" >' +
                '</map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecordOnePartner);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        assert.strictEqual(map.$('a.btn.btn-primary').attr('href'), 'https://www.google.com/maps/dir/?api=1&waypoints=10.5,10', 'The link\'s URL should contain unqiue sets of coordinates');
        await testUtils.dom.click(map.$('.leaflet-marker-icon'));
        assert.strictEqual(map.$('div.leaflet-popup').find('a.btn.btn-primary').attr('href'), 'https://www.google.com/maps/dir/?api=1&destination=10.5,10', 'The link\'s URL should only contain unqiue sets of coordinates');
        map.destroy();
    });

    QUnit.test('testing the size of the map', async function (assert) {
        assert.expect(1);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map></map>',
            mockRPC: function () {
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            },
        });

        assert.strictEqual($('.o_map_container').height(), $('.o_content').height(),
            'The map should be the same height as the content div');
        map.destroy();
    });

    QUnit.test('test the position of pin', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            },
        });

        const renderer = map.renderer.componentRef.comp;
        assert.strictEqual(renderer.markers.length, 1,
            'Should have one marker created');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');
        assert.strictEqual(renderer.markers[0].getLatLng().lat, 10,
            'The latitude should be the same as the record');
        assert.strictEqual(renderer.markers[0].getLatLng().lng, 10.5,
            'The longitude should be the same as the record');

        map.destroy();
    });

    /**
     * data: two located records
     * Create an empty map
     */
    QUnit.test('Create of a empty map', async function (assert) {
        assert.expect(9);

        const map = await createView({
            View: MapView,
            model: 'res.partner',
            data: this.data,
            arch: '<map></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            }
        });
        const renderer = map.renderer.componentRef.comp;
        assert.notOk(map.model.resPartnerField, 'the resPartnerField should not be set');

        assert.containsOnce(map, '.o_map_view',
            '1 div should have the class "o_map_view"');
        assert.containsOnce(map, '.leaflet-map-pane',
            "If the map exists this div should exist");
        assert.ok(renderer.leafletMap,
            'If the map exists this property should be initialized');
        assert.ok($('.leaflet-pane .leaflet-tile-pane').children().length,
            'The map tiles should have been happened to the DOM');
        // if element o_map_container has class leaflet-container then
        // the map is mounted
        assert.hasClass(map.el.querySelector('.o_map_container'),
            'leaflet-container', 'the map should be in the DOM');

        assert.strictEqual(renderer.polylines.length, 0,
            'Should have no polylines');
        assert.strictEqual($('.leaflet-overlay-pane').children().length, 0,
            'Should have no showing route');
        assert.strictEqual(renderer.leafletMap.getZoom(), 2,
            'The level of zoom should should be at it\'s minimum');

        map.destroy();
    });

    /**
     * two located records
     * without routing or default_order
     * normal marker icon
     * test the click on them
     */

    QUnit.test('Create view with normal marker icons', async function (assert) {
        assert.expect(6);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.notOk(map.renderer.props.numbering,
            'the numbering option should not be enabled');
        assert.notOk(map.model.routing,
            'The routing option should not be enabled');

        assert.containsOnce(map, '.leaflet-marker-icon',
            'There should be 1 marker');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route showing');

        await testUtils.dom.click(map.$('.leaflet-marker-icon'));

        assert.strictEqual(map.$('.leaflet-popup-pane').children().length, 1,
            'Should have one showing popup');

        await testUtils.dom.click(map.$('div.leaflet-container'));

        assert.notOk(map.renderer.componentRef.comp.markers[0].isPopupOpen(),
            'The marker\'s popup should be close');

        map.destroy();
    });

    /**
     * two located records
     * with default_order
     * no numbered icon
     * test click on them
     * asserts that the rpc receive the right parameters
     */
    QUnit.test('Create a view with default_order', async function (assert) {
        assert.expect(7);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" default_order="name"></map>',
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        assert.strictEqual(args.sort, 'name ASC',
                            'The sorting order should be on the field name in a ascendant way');
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            },
        });
        assert.ok(map.renderer.props.numbering === false,
            'the numbering option should not be enabled');
        assert.notOk(map.model.routing,
            'The routing option should not be enabled');
        assert.containsOnce(map, 'div.leaflet-marker-icon',
            'There should be 1 marker');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');
        assert.strictEqual(map.$('.leaflet-popup-pane').children().length, 0,
            'Should have no showing popup');
        await testUtils.dom.click(map.$('div.leaflet-marker-icon'));
        assert.strictEqual(map.$('.leaflet-popup-pane').children().length, 1,
            'Should have one showing popup');

        map.destroy();
    });

    /**
     * two locted records
     * with routing enabled
     * numbered icon
     * test click on route
     */
    QUnit.test('Create a view with routing', async function (assert) {
        assert.expect(9);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.ok(map.renderer.props.numbering,
            'The numbering option should be enabled');
        assert.ok(map.model.routing,
            'The routing option should be enabled');

        assert.strictEqual(map.model.numberOfLocatedRecords, 2,
            'Should have 2 located Records');
        assert.strictEqual(map.renderer.props.routeInfo.routes.length, 1,
            'Should have 1 computed route');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');
        assert.strictEqual(map.$('path.leaflet-interactive').attr('stroke'), 'blue',
            'The route should be blue if it has not been clicked');
        assert.strictEqual(map.$('path.leaflet-interactive').attr('stroke-opacity'), '0.3',
            'The opacity of the polyline should be 0.3');
        map.renderer.componentRef.comp.polylines[0].fire('click');
        assert.strictEqual(map.$('path.leaflet-interactive').attr('stroke'), 'darkblue',
            'The route should be darkblue after being clicked');
        assert.strictEqual(map.$('path.leaflet-interactive').attr('stroke-opacity'), '1',
            'The opacity of the polyline should be 1');

        map.destroy();
    });

    QUnit.test('Create a view with routingError', async function (assert) {
        assert.expect(1);

        testUtils.mock.unpatch(MapModel);
        testUtils.mock.patch(MapModel, {
            _maxBoxAPI() {
                this.data.routingError = "this is test warning";
                this.data.routeInfo = { routes: [] };
                return Promise.resolve();
            }
        });

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve([]);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        assert.containsOnce(map, '.o_map_view > .o-map-alert',
            'should have alert');

        map.destroy();
    });

    /**
     * routing with token and one located record
     * No route
     */
    QUnit.test('create a view with routing and one located record', async function (assert) {
        assert.expect(2);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.ok(map.model.routing,
            'The routing option should be enabled');
        assert.strictEqual(map.renderer.props.routeInfo.routes.length, 0,
            'Should have no computed route');

        map.destroy();
    });

    /**
     * no mapbox token
     * assert that the view uses the right api and routes
     */
    QUnit.test('CreateView with empty mapbox token setting', async function (assert) {
        assert.expect(3);
        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].recordWithouthPartner);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].emptyRecords);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: ''
            },
        });
        assert.strictEqual(map.model.data.mapBoxToken, '',
            'The token should be an empty string');
        assert.strictEqual(map.renderer.componentRef.comp.apiTilesRoute,
            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'With no token the route for fetching tiles should be "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"');
        assert.strictEqual(map.renderer.props.mapBoxToken, '',
            'The token should be an empty string');

        map.destroy();
    });

    /**
     * wrong mapbox token
     * assert that the view uses the openstreetmap api
     */
    QUnit.test('Create a view with wrong map box setting', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'vrve'
            },
        });
        assert.strictEqual(map.model.data.mapBoxToken, '',
            'The token should be an empty string');
        assert.strictEqual(map.renderer.componentRef.comp.apiTilesRoute,
            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'With no token the route for fetching tiles should be "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"');
        assert.strictEqual(map.renderer.props.mapBoxToken, '',
            'The token should be an empty string');

        map.destroy();
    });

    /**
     * wrong mapbox token fails at catch at route computing
     */
    QUnit.test('create a view with wrong map box setting and located records', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'frezfre'
            },
        });
        assert.strictEqual(map.model.data.mapBoxToken, '',
            'The token should be an empty string');
        assert.strictEqual(map.renderer.componentRef.comp.apiTilesRoute,
            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'With no token the route for fetching tiles should be "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"');
        assert.strictEqual(map.renderer.props.mapBoxToken, '',
            'The token should be an empty string');

        map.destroy();
    });

    /**
     * create view with right map box token
     * assert that the view uses the map box api
     */
    QUnit.test('Create a view with the right map box token', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].recordWithouthPartner);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].emptyRecords);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.model.data.mapBoxToken, 'token',
            'The token should be the right token');
        assert.strictEqual(map.renderer.componentRef.comp.apiTilesRoute,
            'https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}',
            'With no token the route for fetching tiles should be "https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}"');
        assert.strictEqual(map.renderer.props.mapBoxToken, 'token',
            'The token should be the right token');

        map.destroy();
    });

    /**
     * data: two located records
     */
    QUnit.test('Click on pin shows popup, click on another shuts the first and open the other', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.notOk(map.$('.leaflet-pane .leaflet-popup-pane').children().length,
            'The popup div should be empty');

        await testUtils.dom.click(map.$('div.leaflet-marker-icon'));
        assert.strictEqual(map.$('.leaflet-popup-pane').children().length, 1,
            'The popup div should contain one element');

        await testUtils.dom.click(map.$el.find('.leaflet-map-pane'));
        // wait for the popup's destruction which takes a certain time...
        for (let i = 0; i < 15; i++) {
            await testUtils.nextTick();
        }
        assert.notOk(map.$('.leaflet-pane .leaflet-popup-pane').children().length,
            'The popup div should be empty');

        map.destroy();
    });

    /**
     * data: two located records
     * asserts that all the records are shown on the map
     */
    QUnit.test('assert that all the records are shown on the map', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        const mapX = map.$('.leaflet-map-pane')[0]._leaflet_pos.x;
        const mapY = map.$('.leaflet-map-pane')[0]._leaflet_pos.y;
        assert.ok(mapX - map.$('div.leaflet-marker-icon').eq(0)[0]._leaflet_pos.x < 0,
            'If the marker is currently shown on the map, the subtraction of latitude should be under 0');
        assert.ok(mapY - map.$('div.leaflet-marker-icon').eq(0)[0]._leaflet_pos.y < 0);
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');

        map.destroy();
    });

    /**
     * data: two located records
     * asserts that the right fields are shown in the popup
     */
    QUnit.test('Content of the marker popup with one field', async function (assert) {
        assert.expect(7);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch:
                `<map res_partner="partner_id" routing="true" hide_name="true" hide_address="true">
                    <field name="display_name" string="Name"/>
                </map>`,
            viewOptions: {
                actionViews: [{ type: 'form' }]
            },
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        assert.ok(args.fields.includes('display_name'));
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.renderer.props.fieldNamesMarkerPopup[0].fieldName, "display_name");

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0)[0]);

        assert.strictEqual(map.renderer.props.fieldNamesMarkerPopup.length, 1,
            'fieldsMarkerPopup should contain one field');
        assert.strictEqual(map.$('tbody').children().children().length, 3,
            'The popup should have one field');
        assert.strictEqual(map.$('tbody').children().children().eq(0).prop("innerText"), 'Name',
            'The first element of the table should \'Name\'');
        assert.strictEqual(map.$('tbody').children().children().eq(2).prop("innerText"), 'Foo',
            'The second element of the table should \'Foo\'');
        assert.strictEqual(map.$('div.center').children().length, 3,
            'The popup should contain 2 buttons and one divider');

        map.destroy();
    });

    QUnit.test('Content of the marker popup with date time', async function (assert) {
        assert.expect(2);
        const unpatchDate = patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11, UTC+1

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch:
                `<map res_partner="partner_id" routing="true" hide_name="true" hide_address="true">
                    <field name="display_name" string="Name"/>
                    <field name="scheduled_date" string="Scheduled Date"/>
                </map>`,
            viewOptions: {
                actionViews: [{ type: 'form' }]
            },
            mockRPC: function (route, args) {
                switch (route) {
                    case '/web/dataset/search_read':
                        assert.ok(args.fields.includes('display_name'));
                        return Promise.resolve(this.data['project.task'].oneRecordFieldDateTime);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token',
                getTZOffset: function () {
                    return 60;
                },
            },
        });

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0)[0]);
        assert.strictEqual(map.$('tbody').children().eq(1).children().eq(2).prop("innerText"), '02/07/2022 22:09:31',
            'The second element of the table should \'02/07/2022 22:09:31\'');

        map.destroy();
        unpatchDate();
    });

    /**
     * data: two located records
     * asserts that no field is shown in popup
     */
    QUnit.test('Content of the marker with no field', async function (assert) {
        assert.expect(2);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true" hide_name="true" hide_address="true"></map>',
            viewOptions: {
                actionViews: [{ type: 'form' }]
            },
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0)[0]);

        assert.strictEqual(map.$('tbody').children().length, 0,
            'The popup should have only the button');
        assert.strictEqual(map.$('div.center').children().length, 3,
            'The popup should contain 2 buttons and one divider');

        map.destroy();
    });

    QUnit.test('Attribute: hide_name', async function (assert) {
        assert.expect(2);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true" hide_name="true"></map>',
            mockRPC: route => {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0)[0]);

        assert.containsOnce(map, 'tbody > tr',
            'The popup should have one field');
        assert.strictEqual(map.$('tbody tr .contentName').text().trim(), 'Address',
            'The popup should have address field');

        map.destroy();
    });

    QUnit.test('Render partner address field in popup', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true" hide_name="true"></map>',
            mockRPC: route => {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0)[0]);

        assert.containsOnce(map, 'tbody tr',
            'The popup should have one field');
        assert.strictEqual(map.$('tbody tr .contentName').text().trim(), 'Address',
            'The popup should have address field');
        assert.strictEqual(map.$('tbody tr .contentString').text().trim(), 'Chaussée de Namur 40, 1367, Ramillies',
            'The popup should have correct address');

        map.destroy();
    });

    QUnit.test('Hide partner address field in popup', async function (assert) {
        assert.expect(3);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true" hide_address="true"></map>',
            mockRPC: route => {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0)[0]);

        assert.containsOnce(map, 'tbody tr',
            'The popup should have one field');
        assert.strictEqual(map.$('tbody tr .contentName').text().trim(), 'Name',
            'The popup should have name field');
        assert.strictEqual(map.$('tbody tr .contentString').text().trim(), 'Foo',
            'The popup should have correct address');

        map.destroy();
    });

    QUnit.test('Handle records of same co-ordinates in marker', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"/>',
            mockRPC: route => {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].twoRecords);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        assert.containsOnce(map, 'div.leaflet-marker-icon',
            "There should be a one marker");
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            "There should be a marker for two records");

        await testUtils.dom.click(map.$('div.leaflet-marker-icon'));

        assert.containsOnce(map, 'tbody tr',
            "The popup should have one field");
        assert.strictEqual(map.$('tbody tr .contentName').text().trim(), 'Address',
            "The popup should have address field");

        map.destroy();
    });

    QUnit.test('Pager', async function (assert) {
        assert.expect(4);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"></map>',
            mockRPC: route => {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve({
                            length: 101,
                            records: _.range(1, 101).map(i => { return { id: i, name: 'project', partner_id: [i] }; })
                        });
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(_.range(1, 101).map(i => {
                            return { id: i, name: 'Foo', 'partner_latitude': 10.0, 'partner_longitude': 10.5 };
                        }));
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.containsOnce(map, '.o_pager');
        assert.strictEqual(testUtils.controlPanel.getPagerValue(map), "1-80",
            "current pager value should be 1-20");
        assert.strictEqual(testUtils.controlPanel.getPagerSize(map), "101",
            "current pager limit should be 21");

        await testUtils.controlPanel.pagerNext(map);

        assert.strictEqual(testUtils.controlPanel.getPagerValue(map), "81-101",
            "pager value should be 21-40");

        map.destroy();
    });

    QUnit.test('New domain', async function (assert) {
        assert.expect(18);

        this.data['project.task'].records = [
            { id: 1, name: "FooProject", sequence: 1, partner_id: 1 },
            { id: 2, name: 'BarProject', sequence: 2, partner_id: 2 },
        ];
        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing ="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return this._super.apply(this, arguments);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].twoRecordsAddressNoCoordinates);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        assert.strictEqual(map.model.data.records.length, 2,
            'There should be 2 records');
        assert.containsOnce(map.$('.leaflet-overlay-pane'), 'path',
            'There should be one route displayed');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');

        await map.update({ domain: [['name', '=', 'FooProject']] });

        const renderer = map.renderer.componentRef.comp;
        assert.strictEqual(map.model.data.records.length, 1,
            'There should be 1 record');
        assert.strictEqual(renderer.polylines.length, 0,
            'There should be no road computed');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');
        assert.strictEqual(renderer.markers.length, 1,
            'There should be 1 marker generated');
        assert.containsOnce(map, 'div.leaflet-marker-icon',
            'There should be 1 marker on the map');

        await map.update({ domain: [['name', '=', 'Foofezfezf']] });

        assert.strictEqual(map.model.data.records.length, 0,
            'There should be no record');
        assert.strictEqual(renderer.polylines.length, 0,
            'There should be no road computed');
        assert.containsNone(map.$('.leaflet-overlay-pane'), 'path',
            'There should be no route on the map');
        assert.strictEqual(renderer.markers.length, 0,
            'There should be no marker generated');
        assert.containsNone(map, 'div.leaflet-marker-icon',
            'There should be 0 marker on the map');

        await map.update({ domain: [['name', 'like', 'Project']] });

        assert.strictEqual(map.model.data.records.length, 2,
            'There should be 2 record');
        assert.strictEqual(renderer.polylines.length, 1,
            'There should be one road computed');
        assert.containsOnce(map.$('.leaflet-overlay-pane'), 'path',
            'There should be 1 route on the map');
        assert.strictEqual(renderer.markers.length, 1,
            'There should be 1 marker generated');
        assert.strictEqual(map.$('div.leaflet-marker-icon .o_map_marker_badge').text(), '2',
            'There should be a marker for two records');

        map.destroy();
    });

    QUnit.test('Toggle grouped pin lists', async function (assert) {
        assert.expect(13);

        const records = this.data['project.task'].threeRecords;
        const partners = this.data['res.partner'].twoRecordsAddressCoordinates;
        for (const record of records.records) {
            // add name on partner_id to have name_get like value
            record.partner_id.push(partners.find(x => x.id === record.partner_id[0]).name);
        }

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"/>',
            async mockRPC(route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return records;
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return partners;
                }
            },
            session: {
                map_box_token: 'token'
            },
            groupBy: ['partner_id'],
        });

        assert.containsN(map, '.o_pin_list_group_header', 2, 'Should have 2 groups');
        assert.strictEqual(map.$('.o_pin_list_group_header').text(), 'BarFoo');
        assert.containsN(map, '.o_pin_list_details', 2);
        assert.containsN(map, '.o_pin_list_details li', 3);
        assert.strictEqual(map.$('.o_pin_list_details').text(), 'FooProjectFooBarProjectBarProject');

        await testUtils.dom.click(map.$('.o_pin_list_group_header:eq(1)'));

        assert.containsN(map, '.o_pin_list_group_header', 2, 'Should still have 2 groups');
        assert.containsOnce(map, '.o_pin_list_details');
        assert.containsN(map, '.o_pin_list_details li', 2);
        assert.strictEqual(map.$('.o_pin_list_details').text(), 'FooProjectFooBarProject');

        await testUtils.dom.click(map.$('.o_pin_list_group_header:eq(0)'));

        assert.containsNone(map, '.o_pin_list_details');

        await testUtils.dom.click(map.$('.o_pin_list_group_header:eq(1)'));

        assert.containsOnce(map, '.o_pin_list_details');
        assert.containsOnce(map, '.o_pin_list_details li');
        assert.strictEqual(map.$('.o_pin_list_details').text(), 'BarProject');

        map.destroy();
    });

    QUnit.test('Change groupBy', async function (assert) {
        assert.expect(13);

        const records = this.data['project.task'].threeRecords;
        const partners = this.data['res.partner'].twoRecordsAddressCoordinates;
        for (const record of records.records) {
            // add name on partner_id to have name_get like value
            record.partner_id.push(partners.find(x => x.id === record.partner_id[0]).name);
        }

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"/>',
            archs: {
                'project.task,false,search': `
                    <search>
                        <filter string="Partner" name="partner_id" context="{'group_by': 'partner_id'}"/>
                        <filter string="Name" name="display_name" context="{'group_by': 'display_name'}"/>
                    </search>
                `,
            },
            session: {
                map_box_token: 'token'
            },
            async mockRPC(route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return records;
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return partners;
                }
            },
        });

        assert.containsNone(map, '.o_pin_list_group_header', 'Should not have any groups');

        await toggleGroupByMenu(map.el);
        await toggleMenuItem(map.el, 'Partner');

        assert.containsN(map, '.o_pin_list_group_header', 2, 'Should have 2 groups');
        assert.strictEqual(map.$('.o_pin_list_group_header').text(), 'BarFoo');
        // Groups should be loaded too
        assert.containsN(map, '.o_pin_list_details li', 3);
        assert.strictEqual(map.$('.o_pin_list_details').text(), 'FooProjectFooBarProjectBarProject');

        await toggleMenuItem(map.el, 'Name');

        assert.strictEqual(map.$('.o_pin_list_group_header').text(), 'BarFoo', 'Should not have changed');
        assert.strictEqual(map.$('.o_pin_list_details').text(), 'FooProjectFooBarProjectBarProject');

        await toggleMenuItem(map.el, 'Partner');

        assert.containsN(map, '.o_pin_list_group_header', 3, 'Should have 3 groups');
        assert.strictEqual(map.$('.o_pin_list_group_header').text(), 'FooProjectBarProjectFooBarProject');
        assert.strictEqual(map.$('.o_pin_list_details').text(), 'FooProjectBarProjectFooBarProject');
        assert.containsOnce(map, '.o_pin_list_details:eq(0) li');
        assert.containsOnce(map, '.o_pin_list_details:eq(1) li');
        assert.containsOnce(map, '.o_pin_list_details:eq(2) li');

        map.destroy();
    });

    //--------------------------------------------------------------------------
    // Controller testing
    //--------------------------------------------------------------------------

    QUnit.test('Click on open button switches to form view', async function (assert) {
        assert.expect(7);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            viewOptions: {
                actionViews: [{ type: 'form' }]
            },
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });
        testUtils.mock.intercept(map, 'switch_view', function (event) {
            assert.strictEqual(event.name, 'switch_view',
                'The custom event should be \'switch_view\'');
            assert.strictEqual(event.data.view_type, 'form',
                'The view switched to should be form');
            assert.strictEqual(event.data.res_id, 1,
                'The record\'s id should be 1');
            assert.strictEqual(event.data.mode, 'readonly',
                'The mode should be readonly');
            assert.strictEqual(event.data.model, 'project.task',
                'The form view should be on the \'res.partner\' model');
        });
        testUtils.mock.intercept(map, 'open_clicked', function (event) {
            assert.deepEqual(event.data.ids, [1], 'The record\'s id should be 1');

        }, true);

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0));
        await testUtils.dom.click(map.$('div.center').children().eq(0));

        assert.containsOnce(map.$('div.leaflet-popup-pane'), 'button.btn.btn-primary.o_open',
            'The button should be present in the dom');

        map.destroy();
    });

    QUnit.test('Test the lack of open button', async function (assert) {
        assert.expect(1);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0));

        assert.containsNone(map.$('div.leaflet-popup-pane'), 'button.btn.btn-primary.open',
            'The button should not be present in the dom');

        map.destroy();
    });

    QUnit.test('attribute panel_title on the arch should display in the pin list', async function (assert) {
        assert.expect(1);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" panel_title="AAAAAAAAAAAAAAAAA"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].oneRecord);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
            },
        });
        assert.strictEqual(map.$('.o_pin_list_container .o_pin_list_header span').text(),
            'AAAAAAAAAAAAAAAAA');

        map.destroy();
    });

    QUnit.test('Test using a field other than partner_id for the map view', async function (assert) {
        assert.expect(1);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="another_partner_id"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(this.data['project.task'].anotherPartnerId);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(this.data['res.partner'].oneLocatedRecord);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
        });

        await testUtils.dom.click(map.$('div.leaflet-marker-icon').eq(0));

        assert.containsNone(map.$('div.leaflet-popup-pane'), 'button.btn.btn-primary.open',
            'The button should not be present in the dom');

        map.destroy();
    });

    QUnit.test('Check Google Maps URL is updating on domain change', async function (assert) {
        assert.expect(2);
        this.data['project.task'].records = [
            {id: 1, name: "FooProject", sequence: 1, partner_id: 2},
            {id: 2, name: 'BarProject', sequence: 2, partner_id: 3},
        ];
        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id"/>',
        });
        assert.strictEqual(map.$('a.btn.btn-primary').attr('href'), 'https://www.google.com/maps/dir/?api=1&waypoints=10,10.5|11,11.5',
            'The link\'s URL initially should contain the coordinates for all records');
        //apply domain and check that the Google Maps URL on the button reflects the changes
        await map.update({domain: [['name', '=', 'FooProject']]});
        assert.strictEqual(map.$('a.btn.btn-primary').attr('href'), 'https://www.google.com/maps/dir/?api=1&waypoints=10,10.5',
            'The link\'s URL after domain is applied should only contain coordinates for filtered records');
        map.destroy();
    });

    QUnit.test('Check number on markers are correct when group by', async function (assert) {
        assert.expect(3);

        const records = this.data['project.task'].threeRecords;
        const partners = this.data['res.partner'].twoRecordsAddressCoordinates;
        partners[0].partner_latitude = 20.0;

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true"></map>',
            mockRPC: function (route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(records);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(partners);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
            groupBy: ['partner_id'],
        });

        const [first, second] = $('div.leaflet-marker-icon .o_number_icon');
        assert.strictEqual($(first.childNodes[0]).text(), '2', 'The number of the last record for this partner is 2, so the displayed number_icon should be 2.');
        assert.strictEqual($(first.childNodes[1]).text(), '2', 'There are two records for this partner, so the marker badge should be 2.');
        assert.strictEqual($(second.childNodes[0]).text(), '1', 'The number of the only record for this partner is 1, so the displayed number_icon should be 1.');

        map.destroy();
    });

    QUnit.test('Test groupby responsible displays correct group names', async function (assert) {
        assert.expect(2);

        const tasks = this.data['project.task'].twoRecords;
        const partners = this.data['res.partner'].twoRecordsAddressCoordinates;
        const users = this.data['res.users'].twoRecords.records;
        const usersNameGet = users.map(user => [user.id, user.name]);

        const map = await createView({
            View: MapView,
            model: 'project.task',
            data: this.data,
            arch: '<map res_partner="partner_id" routing="true">' +
                      '<field name="user_ids" string="User"/>' +
                  '</map>',
            mockRPC(route) {
                switch (route) {
                    case '/web/dataset/search_read':
                        return Promise.resolve(tasks);
                    case '/web/dataset/call_kw/res.partner/search_read':
                        return Promise.resolve(partners);
                    case '/web/dataset/call_kw/res.users/name_get':
                        return Promise.resolve(usersNameGet);
                }
                return Promise.resolve();
            },
            session: {
                map_box_token: 'token'
            },
            groupBy: ['user_ids'],
        });

        const [header, group1, group2] = $('.o_pin_list_container').children();

        assert.strictEqual(group1.childNodes[0].textContent, users[0].name, 'The first group should be named like the first user.');
        assert.strictEqual(group2.childNodes[0].textContent, users[1].name, 'The second group should be named like the second user.');

        map.destroy();
    });
});

});
