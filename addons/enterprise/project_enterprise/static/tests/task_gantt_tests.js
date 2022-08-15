/** @odoo-module */

import { createView } from "web.test_utils";
import { Domain } from "@web/core/domain";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { TaskGanttView } from "@project_enterprise/js/task_gantt_view";

const actualDate = new Date(2021, 5, 22, 8, 0, 0);
const initialDate = new Date(actualDate.getTime() - actualDate.getTimezoneOffset() * 60 * 1000);
const ganttViewParams = {
    arch: `<gantt date_start="start" date_stop="stop"/>`,
    domain: Domain.FALSE,
    groupBy: [],
    model: "task",
    View: TaskGanttView,
    viewOptions: { initialDate },
    mockRPC: function (route, args) {
        if (args.method === 'search_milestone_from_task') {
            return Promise.resolve([]);
        }
        return this._super.apply(this, arguments);
    },
};

QUnit.module("Views > GanttView > TaskGantt", {
    beforeEach() {
        ganttViewParams.data = {
            task: {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                    start: { string: "Start Date", type: "datetime" },
                    stop: { string: "Start Date", type: "datetime" },
                    time: { string: "Time", type: "float" },
                    user_ids: {
                        string: "Assigned to",
                        type: "many2one",
                        relation: "res.users",
                    },
                    stuff_id: {
                        string: "Stuff",
                        type: "many2one",
                        relation: "stuff",
                    },
                    active: { string: "active", type: "boolean", default: true },
                },
                records: [
                    {
                        id: 1,
                        name: "Blop",
                        start: "2021-06-14 08:00:00",
                        stop: "2021-06-24 08:00:00",
                        user_ids: 100,
                    },
                    {
                        id: 2,
                        name: "Yop",
                        start: "2021-06-02 08:00:00",
                        stop: "2021-06-12 08:00:00",
                        user_ids: 101,
                        stuff_id: 1,
                    },
                ],
            },
            "res.users": {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 100, name: "Jane Doe" },
                    { id: 101, name: "John Doe" },
                ],
            },
            stuff: {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                },
                records: [{ id: 1, name: "Bruce Willis" }],
            },
        };
    },
});

QUnit.test("not user_ids grouped: empty groups are displayed first", async (assert) => {
    assert.expect(1);
    const gantt = await createView({ ...ganttViewParams, groupBy: ["stuff_id"] });
    registerCleanup(gantt.destroy);

    assert.deepEqual(
        [...gantt.el.querySelectorAll(".o_gantt_row_container .o_gantt_row_sidebar")].map(
            (el) => el.innerText
        ),
        ["Undefined Stuff", "Bruce Willis"],
        "'Undefined Stuff' should be the first group"
    );
});

QUnit.test("not user_ids grouped: no empty group if no records", async (assert) => {
    assert.expect(1);
    // delete the record having no stuff_id
    ganttViewParams.data.task.records.splice(0, 1);
    const gantt = await createView({ ...ganttViewParams, groupBy: ["stuff_id"] });
    registerCleanup(gantt.destroy);

    assert.deepEqual(
        [...gantt.el.querySelectorAll(".o_gantt_row_container .o_gantt_row_sidebar")].map(
            (el) => el.innerText
        ),
        ["Bruce Willis"],
        "should not have an 'Undefined Stuff' group"
    );
});

QUnit.test("user_ids grouped: specific empty group added, even if no records", async (assert) => {
    assert.expect(1);
    const gantt = await createView({ ...ganttViewParams, groupBy: ["user_ids"] });
    registerCleanup(gantt.destroy);

    assert.deepEqual(
        [...gantt.el.querySelectorAll(".o_gantt_row_container .o_gantt_row_sidebar")].map(
            (el) => el.innerText
        ),
        ["Unassigned Tasks", "Jane Doe", "John Doe"],
        "'Unassigned Tasks' should be the first group, even if no record exist without user_ids"
    );
});

QUnit.test("[user_ids, ...] grouped", async (assert) => {
    assert.expect(1);
    // add an unassigned task (no user_ids) that has a linked stuff
    ganttViewParams.data.task.records.push({
        id: 3,
        name: "Gnop",
        start: "2021-06-02 08:00:00",
        stop: "2021-06-12 08:00:00",
        stuff_id: 1,
    });
    const gantt = await createView({ ...ganttViewParams, groupBy: ["user_ids", "stuff_id"] });
    registerCleanup(gantt.destroy);

    assert.deepEqual(
        [...gantt.el.querySelectorAll(".o_gantt_row_container .o_gantt_row_sidebar")].map((el) =>
            el.innerText.trim()
        ),
        [
            "Unassigned Tasks",
            "Undefined Stuff",
            "Bruce Willis",
            "Jane Doe",
            "Undefined Stuff",
            "John Doe",
            "Bruce Willis",
        ]
    );
});

QUnit.test("[..., user_ids(, ...)] grouped", async (assert) => {
    assert.expect(1);
    const gantt = await createView({ ...ganttViewParams, groupBy: ["stuff_id", "user_ids"] });
    registerCleanup(gantt.destroy);

    assert.deepEqual(
        [...gantt.el.querySelectorAll(".o_gantt_row_container .o_gantt_row_sidebar")].map((el) =>
            el.innerText.trim()
        ),
        [
            "Undefined Stuff",
            "Unassigned Tasks",
            "Jane Doe",
            "Bruce Willis",
            "Unassigned Tasks",
            "John Doe",
        ]
    );
});

QUnit.test('Empty groupby "Assigned To" and "Project" can be rendered', async function (assert) {
    ganttViewParams.data = {
        task: {
            fields: {
                id: {string: 'ID', type: 'integer'},
                name: {string: 'Name', type: 'char'},
                start: {string: 'Start Date', type: 'datetime'},
                stop: {string: 'Stop Date', type: 'datetime'},
                project_id: {string: 'Project', type: 'many2one', relation: 'projects'},
                user_ids: {string: 'Assignees', type: 'many2one', relation: 'users'},
            },
            records: [],
        },
    };

    assert.expect(1);
    var gantt = await createView({
        ...ganttViewParams,
        groupBy: ['user_ids', 'project_id'],
    });
    assert.containsN(gantt, ".o_gantt_row", 2);
    gantt.destroy();
});
