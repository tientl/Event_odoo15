/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useEffect, useService } from "@web/core/utils/hooks";
import { capitalize, sprintf } from "@web/core/utils/strings";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView, useViewArch } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { OnboardingBanner } from "@web/views/onboarding_banner";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";
import { DashboardArchParser } from "./dashboard_arch_parser";
import { DashboardCompiler } from "./dashboard_compiler/dashboard_compiler";
import { DashboardModel } from "./dashboard_model";
import { DashboardStatistic } from "./dashboard_statistic/dashboard_statistic";
import { ViewWidget } from "./view_widget";
import { ViewWrapper } from "./view_wrapper/view_wrapper";

const { Component } = owl;

const viewRegistry = registry.category("views");

const SUB_VIEW_CONTROL_PANEL_DISPLAY = {
    "bottom-right": false,
    "top-left": false,
    "top-right": false, // --> top: false
    adaptToScroll: false,
};

const GRAPH_VIEW_PROPS = {
    displayGroupByMenu: true,
    displayScaleLabels: false,
};

const VIEW_PROPS = {
    graph: GRAPH_VIEW_PROPS,
};

export class DashboardView extends Component {
    setup() {
        this._viewService = useService("view");
        this.action = useService("action");
        this.subViewsRenderKey = 1;

        const { resModel, arch, fields } = this.props;
        const processedArch = useViewArch(arch, {
            compile: (arch) => new this.constructor.Compiler().compileArch(arch),
            extract: (arch) => new this.constructor.ArchParser().parse(arch, fields),
        });

        this.template = processedArch.template;
        const { subViewRefs, aggregates, formulae } = processedArch.extracted;
        this.subViews = {};
        Object.keys(subViewRefs).forEach((viewType) => {
            this.subViews[viewType] = {
                ref: subViewRefs[viewType],
                callbackRecorders: {
                    __getLocalState__: new CallbackRecorder(),
                    __getGlobalState__: new CallbackRecorder(),
                    __getContext__: new CallbackRecorder(),
                },
                props: null, // will be generated after the loadViews
            };
            if (this.props.state) {
                this.subViews[viewType].state = this.props.state.subViews[viewType];
            }
        });
        this.aggregates = aggregates;
        this.formulae = formulae;

        useSetupView({
            getLocalState: () => {
                return {
                    subViews: this.callRecordedCallbacks("__getLocalState__"),
                };
            },
            getContext: () => {
                return this.callRecordedCallbacks("__getContext__");
            },
        });

        this.model = useModel(this.constructor.Model, {
            resModel,
            fields,
            aggregates: this.aggregates,
            formulae: this.formulae,
        });

        // Always renew every view
        useEffect(() => {
            this.subViewsRenderKey++;
        });
    }

    async willStart() {
        let loadViewProms = [];
        let additionalMeasures = this.aggregates
            .filter((a) => {
                const { type } = this.props.fields[a.field];
                return type === "many2one";
            })
            .map((a) => a.field);

        const allViews = Object.entries(this.subViews);
        if (!allViews.length) {
            return;
        }
        const resModel = this.props.resModel;
        const loadViewsContext = Object.assign({}, this.props.context);
        const falseRefs = {
            context: {},
            views: [],
        };
        const withRefs = {
            context: {},
            views: [],
        };

        // group loadViews: false on the one side, and each ref on its own
        for (const [type, { ref }] of allViews) {
            if (!ref) {
                falseRefs.views.push([false, type]);
            } else {
                const viewRef = `${type}_view_ref`;
                withRefs.views.push([false, type]);
                withRefs.context[viewRef] = ref;
            }
        }

        [falseRefs, withRefs].forEach((params) => {
            const views = params.views;
            if (!views.length) {
                return;
            }
            const context = Object.assign(loadViewsContext, params.context);
            loadViewProms.push(
                this._viewService
                    .loadViews({ context, views, resModel }, {})
                    .then((viewDescriptions) => {
                        Object.entries(viewDescriptions).forEach(([type, viewInfo]) => {
                            const subView = this.subViews[type];
                            if (!subView) {
                                return;
                            }
                            const context = Object.assign(
                                this.props.context,
                                this.props.context[type] || {}
                            );
                            delete context[type];
                            const { viewId, arch, fields } = viewInfo;
                            subView.props = {
                                viewId,
                                arch,
                                fields,
                                additionalMeasures,
                                context,
                                type,
                            };
                        });
                    })
            );
        });

        await Promise.all(loadViewProms);
    }

    async willUpdateProps(nextProps) {
        const states = this.callRecordedCallbacks("__getLocalState__");
        Object.entries(this.subViews).forEach(([viewType, subView]) => {
            subView.state = states[viewType];
            subView.state.metaData = Object.assign({}, subView.state.metaData);
            if (this.currentMeasure) {
                if (viewType === "graph" || viewType === "cohort") {
                    subView.state.metaData.measure = this.currentMeasure;
                } else if (viewType === "pivot") {
                    subView.state.metaData.activeMeasures = [this.currentMeasure];
                }
            }
        });

        const { comparison, domain } = nextProps;
        for (const [type, subView] of Object.entries(this.subViews)) {
            const context = Object.assign(nextProps.context, nextProps.context[type] || {});
            delete context[type];
            Object.assign(subView.props, { comparison, context, domain });
        }

        const globalStates = this.callRecordedCallbacks("__getGlobalState__");
        for (const [type, subView] of Object.entries(this.subViews)) {
            subView.props = Object.assign({}, subView.props, { globalState: globalStates[type] });
        }
    }

    /**
     * Calls a type of recorded callbacks and aggregates their result.
     * @param {"__getContext__"|"__getLocalState__"|"__getGlobalState__"} name
     * @returns {Object}
     */
    callRecordedCallbacks(name) {
        const result = {};
        for (const [viewType, subView] of Object.entries(this.subViews)) {
            const callbacks = subView.callbackRecorders[name]._callbacks;
            if (callbacks.length) {
                const res = callbacks.reduce((res, c) => {
                    return { ...res, ...c.callback() };
                }, {});
                if (name === "__getGlobalState__") {
                    delete res.useSampleModel;
                }
                result[viewType] = res;
            }
        }
        return result;
    }

    /**
     * Returns the props of the ViewWrapper components.
     * @param {string} viewType
     * @returns {Object}
     */
    getViewWrapperProps(viewType) {
        return {
            callbackRecorders: this.subViews[viewType].callbackRecorders,
            switchView: () => this.openFullscreen(viewType),
            type: viewType,
            viewProps: this.getViewProps(viewType),
        };
    }

    /**
     * Returns the props to pass to the sub view of the given type.
     * @param {string} viewType
     * @returns {Object}
     */
    getViewProps(viewType) {
        const subView = this.subViews[viewType];
        const viewProps =  Object.assign(
            {
                domain: this.props.domain,
                comparison: this.props.comparison,
                resModel: this.props.resModel,
                searchViewArch: this.props.info.searchViewArch,
                searchViewFields: this.props.info.searchViewFields,
                type: viewType,
                display: { controlPanel: SUB_VIEW_CONTROL_PANEL_DISPLAY },
            },
            VIEW_PROPS[viewType],
            subView.props,
            {
                noContentHelp: this.model.useSampleModel ? false : undefined,
                useSampleModel: this.model.useSampleModel,
                state: subView.state,
            }
        );
        // LEGACY CODE: with legacy code removed, we will be sure search defaults cannot be found
        // here (the WithSearch component remove search defaults keys from the view globalContext)
        for (const key in viewProps.context) {
            const searchDefaultMatch = /^search_default_(.*)$/.exec(key);
            if (searchDefaultMatch) {
                delete viewProps.context[key];
                continue;
            }
        }
        return viewProps;
    }

    /**
     * Opens the requested view in an other action, so that it is displayed in
     * full screen.
     * @param {string} viewType
     * @returns {Promise}
     */
    openFullscreen(viewType) {
        const action = {
            domain: this.env.searchModel.globalDomain,
            context: this.props.context,
            name: sprintf(this.env._t("%s Analysis"), capitalize(viewType)),
            res_model: this.model.metaData.resModel,
            type: "ir.actions.act_window",
            views: [[false, viewType]],
            useSampleModel: false, // disable sample data when zooming on a sub view
        };

        return this.action.doAction(action, {
            props: {
                state: this.callRecordedCallbacks("__getLocalState__")[viewType],
                globalState: { searchModel: JSON.stringify(this.env.searchModel.exportState()) },
            },
        });
    }

    /**
     * Handler executed when the user clicks on a statistic.
     * @param {string} statName
     */
    onStatisticChange(statName) {
        const stat = this.model.getStatisticDescription(statName);
        this.currentMeasure = stat.measure;

        if (stat.domain) {
            this.env.searchModel.setDomainParts({
                dashboardMeasure: {
                    domain: stat.domain,
                    facetLabel: stat.domainLabel,
                },
            });
        } else {
            this.env.searchModel.setDomainParts({ dashboardMeasure: null });
        }
    }
}
DashboardView.template = "web_dashboard.DashboardView";
DashboardView.props = standardViewProps;

DashboardView.components = { Layout, DashboardStatistic, ViewWidget, ViewWrapper };

DashboardView.Model = DashboardModel;
DashboardView.ArchParser = DashboardArchParser;
DashboardView.Compiler = DashboardCompiler;
DashboardView.Banner = OnboardingBanner;

DashboardView.type = "dashboard";
DashboardView.display_name = "dashboard";
DashboardView.icon = "fa-tachometer";
DashboardView.multiRecord = true;

DashboardView.searchMenuTypes = ["filter", "comparison", "favorite"];

viewRegistry.add("dashboard", DashboardView);
