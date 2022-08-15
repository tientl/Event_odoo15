/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { Field } from "@web/fields/fields";

export class DashboardStatistic extends owl.Component {
    setup() {
        let currencyId = this.props.currencyId;
        if (!currencyId) {
            const company = useService("company");
            const currentCompanyId = company.currentCompany.id;
            currencyId = session.companies_currency_id[currentCompanyId];
        }

        const formatterOptions = {
            monetary: {
                // in the dashboard view, all monetary values are displayed in the
                // currency of the current company of the user
                currencyId,
                humanReadable: true,
            },
            default: {
                minDigits: 3,
                digits: 2,
            },
        };
        const widget = "widget" in this.props && this.props.widget;
        const formatters = registry.category("formatters");
        let statType;
        if (!widget || formatters.contains(widget)) {
            statType = widget;
            if (!statType) {
                const stat = this.props.model.getStatisticDescription(this.props.name);
                statType = stat.fieldType;
            }
            // Aggregates for many2one always use group operator "count_distinct"
            // and thus must be considered as integers (@see dashboard arch parser)
            statType = statType === "many2one" ? "integer" : statType;
            this.formatOpts = formatterOptions[statType] || formatterOptions.default;
            this.formatter = statType && formatters.get(statType);
        }
        if (!this.formatter) {
            this.widgetName = widget;
        }
        this.formatterString = statType || this.widgetName;
    }

    getNodeAttributes() {
        if (this.env.debug || this.props.help) {
            return {
                "data-tooltip-template": "web_dashboard.DashboardStatisticTooltip",
                "data-tooltip-info": JSON.stringify(this.getTooltipInfo()),
            };
        }
        return null;
    }

    getTooltipInfo() {
        const props = this.props;
        return {
            displayName: props.displayName,
            formatter: this.formatterString,
            help: props.help,
            modifiers: props.modifiers,
            name: props.name,
            statistic: props.model.getStatisticDescription(props.name),
            statisticType: props.statisticType,
            valueLabel: props.valueLabel,
        };
    }

    get hasComparison() {
        return this.props.model.data[this.props.name].variations.length;
    }

    getRawValue(index) {
        return this.props.model.data[this.props.name].values[index];
    }

    formatValue(value) {
        if (isNaN(value)) {
            return " - ";
        }
        return this.formatter(value, this.formatOpts);
    }

    getFakeRecord(index) {
        if (!this.recordId) {
            this.recordId = 1;
        } else {
            this.recordId++;
        }
        const fakeData = {};
        for (const [fName, data] of Object.entries(this.props.model.data)) {
            fakeData[fName] = data.values[index];
        }
        const allFields = Object.assign(
            {},
            this.props.model.metaData.fields,
            this.props.model.metaData.statistics
        );
        for (const field of Object.values(allFields)) {
            field.type = field.fieldType;
        }
        return {
            id: this.recordId,
            viewtype: "dashboard",
            fields: allFields,
            fieldsInfo: {
                dashboard: allFields,
            },
            data: fakeData,
        };
    }

    // Variation
    get rawVariation() {
        return this.props.model.data[this.props.name].variations[0];
    }

    get variationSign() {
        if (!isNaN(this.rawVariation)) {
            return Math.sign(this.rawVariation);
        }
        return false;
    }

    get variation() {
        if (isNaN(this.rawVariation)) {
            return false;
        }
        const percentage = registry.category("formatters").get("percentage");
        return percentage(this.rawVariation);
    }

    // Style
    getBorderClass() {
        if (this.hasComparison) {
            const varSign = this.variationSign;
            if (varSign === 1) {
                return { "border-success": true };
            } else if (varSign === -1) {
                return { "border-danger": true };
            }
        }
    }

    getAttClass() {
        const { statisticType, clickable } = this.props;
        return Object.assign(
            {
                o_aggregate: statisticType === "aggregate",
                o_formula: statisticType === "formula",
                o_clickable: clickable,
            },
            this.getBorderClass()
        );
    }

    get variationClass() {
        if (this.hasComparison) {
            const varSign = this.variationSign;
            if (varSign === 1) {
                return { "o_positive text-success": true };
            } else if (varSign === -1) {
                return { "o_negative text-danger": true };
            } else if (varSign === 0) {
                return { o_null: true };
            }
        }
    }

    onClicked() {
        if (this.props.clickable) {
            this.trigger("change-statistic");
        }
    }
}
DashboardStatistic.template = "web_dashboard.DashboardStatistic";
DashboardStatistic.components = { Field };
