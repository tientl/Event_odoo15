/** @odoo-module alias=documents_spreadsheet.TestData default=0 */

/**
 * Get a basic arch for a pivot, which is compatible with the data given by
 * getBasicData().
 *
 * Here is the pivot created:
 *     A      B      C      D      E      F
 * 1          1      2      12     17     Total
 * 2          Proba  Proba  Proba  Proba  Proba
 * 3  false          15                    15
 * 4  true    11            10     95     116
 * 5  Total   11     15     10     95     131
 */
export function getBasicPivotArch() {
    return `
        <pivot string="Partners">
            <field name="foo" type="col"/>
            <field name="bar" type="row"/>
            <field name="probability" type="measure"/>
        </pivot>`;
}

/**
 * Get a basic arch for a list, which is compatible with the data given by
 * getBasicData().
 *
 * Here is the list created:
 *     A      B      C          D
 * 1  Foo     bar    Date       Product
 * 2  12      True   2016-04-14 xphone
 * 3  1       True   2016-10-26 xpad
 * 4 17       True   2016-12-15 xpad
 * 5 2        False  2016-12-11 xpad
 */
export function getBasicListArch() {
    return `
        <tree string="Partners">
            <field name="foo"/>
            <field name="bar"/>
            <field name="date"/>
            <field name="product_id"/>
        </tree>
    `;
}

export function getBasicData() {
    return {
        "documents.document": {
            fields: {
                name: { string: "Name", type: "char" },
                mimetype: { string: "mimetype", type: "char" },
                raw: { string: "Data", type: "text" },
                thumbnail: { string: "Thumbnail", type: "text" },
                favorited_ids: { string: "Name", type: "many2many" },
                is_favorited: { string: "Name", type: "boolean" },
                mimetype: { string: "Mimetype", type: "char" },
                partner_id: { string: "Related partner", type: "many2one", relation: "partner" },
                owner_id: { string: "Owner", type: "many2one", relation: "partner" },
                handler: {
                    string: "Handler",
                    type: "selection",
                    selection: [["spreadsheet", "Spreadsheet"]],
                },
                previous_attachment_ids: {
                    string: "History",
                    type: "many2many",
                    relation: "ir.attachment",
                },
                tag_ids: { string: "Tags", type: "many2many", relation: "documents.tag" },
                folder_id: { string: "Workspaces", type: "many2one", relation: "documents.folder" },
                res_model: { string: "Model (technical)", type: "char" },
                available_rule_ids: {
                    string: "Rules",
                    type: "many2many",
                    relation: "documents.workflow.rule",
                },
            },
            records: [
                {
                    id: 1,
                    name: "My spreadsheet",
                    raw: "{}",
                    is_favorited: false,
                    folder_id: 1,
                    handler: "spreadsheet",
                },
                {
                    id: 2,
                    name: "",
                    raw: "{}",
                    is_favorited: true,
                    folder_id: 1,
                    handler: "spreadsheet",
                },
            ],
        },
        "ir.model": {
            fields: {
                name: { string: "Model Name", type: "char" },
                model: { string: "Model", type: "char" },
            },
            records: [
                {
                    id: 37,
                    name: "Product",
                    model: "product",
                },
                {
                    id: 40,
                    name: "partner",
                    model: "partner",
                },
            ],
        },
        "documents.folder": {
            fields: {
                name: { string: "Name", type: "char" },
                parent_folder_id: {
                    string: "Parent Workspace",
                    type: "many2one",
                    relation: "documents.folder",
                },
                description: { string: "Description", type: "text" },
            },
            records: [
                {
                    id: 1,
                    name: "Workspace1",
                    description: "Workspace",
                    parent_folder_id: false,
                },
            ],
        },
        "documents.tag": {
            fields: {},
            records: [],
            get_tags: () => [],
        },
        "documents.workflow.rule": {
            fields: {},
            records: [],
        },
        "documents.share": {
            fields: {},
            records: [],
        },
        partner: {
            fields: {
                foo: {
                    string: "Foo",
                    type: "integer",
                    searchable: true,
                    group_operator: "sum",
                },
                bar: { string: "bar", type: "boolean", store: true, sortable: true },
                name: { string: "name", type: "char", store: true, sortable: true },
                date: { string: "Date", type: "date", store: true, sortable: true },
                active: { string: "Active", type: "bool", default: true },
                product_id: {
                    string: "Product",
                    type: "many2one",
                    relation: "product",
                    store: true,
                    sortable: true,
                },
                tag_ids: {
                    string: "Tags",
                    type: "many2many",
                    relation: "tag",
                    store: true,
                    sortable: true,
                },
                probability: {
                    string: "Probability",
                    type: "integer",
                    searchable: true,
                    group_operator: "avg",
                },
                field_with_array_agg: {
                    string: "field_with_array_agg",
                    type: "integer",
                    searchable: true,
                    group_operator: "array_agg",
                },
            },
            records: [
                {
                    id: 1,
                    foo: 12,
                    bar: true,
                    date: "2016-04-14",
                    product_id: 37,
                    probability: 10,
                    field_with_array_agg: 1,
                    tag_ids: [42, 67],
                },
                {
                    id: 2,
                    foo: 1,
                    bar: true,
                    date: "2016-10-26",
                    product_id: 41,
                    probability: 11,
                    field_with_array_agg: 2,
                    tag_ids: [42, 67],
                },
                {
                    id: 3,
                    foo: 17,
                    bar: true,
                    date: "2016-12-15",
                    product_id: 41,
                    probability: 95,
                    field_with_array_agg: 3,
                    tag_ids: [],
                },
                {
                    id: 4,
                    foo: 2,
                    bar: false,
                    date: "2016-12-11",
                    product_id: 41,
                    probability: 15,
                    field_with_array_agg: 4,
                    tag_ids: [42],
                },
            ],
        },
        product: {
            fields: {
                name: { string: "Product Name", type: "char" },
                active: { string: "Active", type: "bool", default: true },
            },
            records: [
                {
                    id: 37,
                    display_name: "xphone",
                },
                {
                    id: 41,
                    display_name: "xpad",
                },
            ],
        },
        tag: {
            fields: {
                name: { string: "Tag Name", type: "char" },
            },
            records: [
                {
                    id: 42,
                    display_name: "isCool",
                },
                {
                    id: 67,
                    display_name: "Growing",
                },
            ],
        },
    };
}
