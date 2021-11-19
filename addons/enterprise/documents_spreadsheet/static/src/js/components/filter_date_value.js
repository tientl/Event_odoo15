odoo.define("documents_spreadsheet.DateFilterValue", function (require) {
    "use strict";

    const { getPeriodOptions } = require("web.searchUtils");
    const { _lt } = require('web.core');
    const dateTypeOptions = {
        quarter: ["first_quarter", "second_quarter", "third_quarter", "fourth_quarter"],
        year: ["this_year", "last_year", "antepenultimate_year"],
    };
    const monthsOptions = [
        { id: "january", description: _lt("January") },
        { id: "february", description: _lt("February") },
        { id: "march", description: _lt("March") },
        { id: "april", description: _lt("April") },
        { id: "may", description: _lt("May") },
        { id: "june", description: _lt("June") },
        { id: "july", description: _lt("July") },
        { id: "august", description: _lt("August") },
        { id: "september", description: _lt("September") },
        { id: "october", description: _lt("October") },
        { id: "november", description: _lt("November") },
        { id: "december", description: _lt("December") },
    ];

    /**
     * Return a list of time options to choose from according to the requested
     * type. Each option contains its (translated) description.
     * @see getPeriodOptions
     * @param {string} type "month" | "quarter" | "year"
     * @returns {Array<Object>}
     */
    function dateOptions(type) {
        if (type === "month") {
            return monthsOptions;
        } else {
            return getPeriodOptions(moment()).filter(({ id }) => dateTypeOptions[type].includes(id));
        }
    }

    class DateFilterValue extends owl.Component {
        dateOptions(type) {
            return type ? dateOptions(type) : [];
        }

        isYear() {
            return this.props.type === "year";
        }

        isSelected(periodId) {
            return [this.props.year, this.props.period].includes(periodId);
        }

        getCurrentDateFilterValue() {
            const period = dateOptions(this.props.type).filter(period => this.isSelected(period.id))
            let value = period.length && period[0].description || ""

            if (!this.isYear()){
                const year = dateOptions("year").filter(period => this.isSelected(period.id))
                value += ` ${year.length && year[0].description || ""}`
            }
            return value
        }

        onPeriodChanged(ev) {
            const value = ev.target.value;
            this.trigger("time-range-changed", {
                /** We need to ensure that a year is set when the period
                 * is selected since the user can bypass the year selection.
                 * If we don't, we might end up with a date filter with year===undefined
                 * which works to setup a pivot domain but is technically incorrect
                 * and will return a bad value on FILTER.VALUE function.
                 * */
                year: this.props.year || this.dateOptions('year')[0].id,
                period: value !== "empty" ? value : undefined,
            });
        }

        onYearChanged(ev) {
            const value = ev.target.value;
            this.trigger("time-range-changed", {
                year: value !== "empty" ? value : undefined,
                period: this.props.period,
            });
        }
    }
    DateFilterValue.template = "documents_spreadsheet.DateFilterValue";

    return DateFilterValue;
});
