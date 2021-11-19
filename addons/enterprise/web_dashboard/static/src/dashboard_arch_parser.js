/** @odoo-module **/

import { XMLParser } from "@web/core/utils/xml";
import * as CompileHelpers from "./dashboard_compiler/compile_helpers";

const SUPPORTED_VIEW_TYPES = ["graph", "pivot", "cohort"];

export class DashboardArchParser extends XMLParser {
    parse(arch, fields) {
        const subViewRefs = {};
        const aggregates = [];
        const formulae = [];
        const nodeIdentifier = CompileHelpers.nodeIdentifier();

        this.visitXML(arch, (node) => {
            if (node.tagName === "view") {
                const type = node.getAttribute("type");
                if (!SUPPORTED_VIEW_TYPES.includes(type)) {
                    throw new Error(`Unsupported viewtype "${type}" in DashboardView`);
                }
                if (type in subViewRefs) {
                    throw new Error(
                        `multiple views of the same type is not allowed. Duplicated type: "${type}".`
                    );
                }
                subViewRefs[type] = node.getAttribute("ref") || false;
            }
            if (node.tagName === "aggregate") {
                const fieldName = node.getAttribute("field");
                const field = fields[fieldName];
                let groupOperator = node.getAttribute("group_operator");

                if (!groupOperator && field.group_operator) {
                    groupOperator = field.group_operator;
                }
                // in the dashboard views, many2one fields are fetched with the
                // group_operator 'count_distinct', which means that the values
                // manipulated client side for these fields are integers

                //TO DO: Discuss with LPE: on legacy we also change the type of the field : field.type = 'integer';
                if (field.type === "many2one") {
                    groupOperator = "count_distinct";
                }

                let measure = node.getAttribute("measure");
                if (measure && measure === "__count__") {
                    measure = "__count";
                }
                aggregates.push({
                    name: node.getAttribute("name"),
                    field: fieldName,
                    domain: node.getAttribute("domain"),
                    domainLabel:
                        node.getAttribute("domain_label") ||
                        node.getAttribute("string") ||
                        node.getAttribute("name"),
                    measure: measure || fieldName,
                    groupOperator,
                });
            }
            if (node.tagName === "formula") {
                nodeIdentifier(node);
                formulae.push({
                    name: node.getAttribute("name") || nodeIdentifier.idFor(),
                    operation: node.getAttribute("value"),
                    domain: node.getAttribute("domain"),
                });
            }
        });
        return { subViewRefs, aggregates, formulae };
    }
}
