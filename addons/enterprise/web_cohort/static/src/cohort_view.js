/* @odoo-module */

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { CohortArchParser } from "./cohort_arch_parser";
import { CohortModel } from "./cohort_model";
import { CohortRenderer } from "./cohort_renderer";

class CohortView extends owl.Component {
    setup() {
        this.actionService = useService("action");

        let modelParams;
        if (this.props.state) {
            modelParams = this.props.state.metaData;
        } else {
            const { arch, fields } = this.props;
            const archInfo = new this.constructor.ArchParser().parse(arch, fields);
            modelParams = {
                additionalMeasures: this.props.additionalMeasures,
                dateStart: archInfo.dateStart,
                dateStartString: archInfo.dateStartString,
                dateStop: archInfo.dateStop,
                dateStopString: archInfo.dateStopString,
                fieldAttrs: archInfo.fieldAttrs,
                fields: this.props.fields,
                interval: archInfo.interval,
                measure: archInfo.measure,
                mode: archInfo.mode,
                resModel: this.props.resModel,
                timeline: archInfo.timeline,
                title: archInfo.title,
            };
        }

        this.model = useModel(this.constructor.Model, modelParams);

        useSetupView({
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
            getContext: () => this.getContext(),
        });
    }

    getContext() {
        const { measure, interval } = this.model.metaData;
        return { cohort_measure: measure, cohort_interval: interval };
    }

    /**
     * @param {Object} row
     */
    onRowClicked(row) {
        if (row.value === undefined) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        const domain = row.domain;
        const views = {};
        for (const [viewId, viewType] of this.env.config.views || []) {
            views[viewType] = viewId;
        }
        function getView(viewType) {
            return [context[`${viewType}_view_id`] || views[viewType] || false, viewType];
        }
        const actionViews = [getView("list"), getView("form")];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.model.metaData.title,
            res_model: this.model.metaData.resModel,
            views: actionViews,
            view_mode: "list",
            target: "current",
            context: context,
            domain: domain,
        });
    }

    /**
     * Export cohort data in Excel file
     */
    async downloadExcel() {
        const {
            title,
            resModel,
            interval,
            measure,
            measures,
            dateStartString,
            dateStopString,
            timeline,
        } = this.model.metaData;
        const { domains } = this.model.searchParams;
        const data = {
            title: title,
            model: resModel,
            interval_string: this.model.intervals[interval].toString(), // intervals are lazy-translated
            measure_string: measures[measure].string,
            date_start_string: dateStartString,
            date_stop_string: dateStopString,
            timeline: timeline,
            rangeDescription: domains[0].description,
            report: this.model.data[0],
            comparisonRangeDescription: domains[1] && domains[1].description,
            comparisonReport: this.model.data[1],
        };
        this.env.services.ui.block();
        try {
            // FIXME: [SAD/JPP] some data seems to be missing from the export in master. (check the python)
            await download({
                url: "/web/cohort/export",
                data: { data: JSON.stringify(data) },
            });
        } finally {
            this.env.services.ui.unblock();
        }
    }

    /**
     * @param {CustomEvent} ev
     */
    onDropDownSelected(ev) {
        this.model.updateMetaData(ev.detail.payload);
    }
}
CohortView.type = "cohort";
CohortView.display_name = "Cohort";
CohortView.icon = "fa-signal";
CohortView.multiRecord = true;
CohortView.template = "web_cohort.CohortView";
CohortView.buttonTemplate = "web_cohort.CohortView.Buttons";
CohortView.components = { Layout, Renderer: CohortRenderer };
CohortView.props = {
    ...standardViewProps,
    additionalMeasures: { type: Array, elements: String, optional: 1 },
};
CohortView.defaultProps = {
    additionalMeasures: [],
};

CohortView.searchMenuTypes = ["filter", "comparison", "favorite"];

CohortView.Model = CohortModel;
CohortView.ArchParser = CohortArchParser;

registry.category("views").add("cohort", CohortView);
