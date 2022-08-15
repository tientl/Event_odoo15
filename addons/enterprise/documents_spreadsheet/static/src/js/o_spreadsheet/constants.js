/** @odoo-module alias=ds.Constants default=0 */

export const DEFAULT_LINES_NUMBER = 20;
export const MAXIMUM_CELLS_TO_INSERT = 20000;

export const formats = {
    day: { in: "DD MMM YYYY", out: "DD/MM/YYYY", display: "DD MMM YYYY", interval: "d" },
    week: { in: "[W]W YYYY", out: "WW/YYYY", display: "[W]W YYYY", interval: "w" },
    month: { in: "MMMM YYYY", out: "MM/YYYY", display: "MMMM YYYY", interval: "M" },
    quarter: { in: "Q YYYY", out: "Q/YYYY", display: "[Q]Q YYYY", interval: "Q" },
    year: { in: "YYYY", out: "YYYY", display: "YYYY", interval: "y" },
};

export const HEADER_STYLE = { fillColor: "#f2f2f2" };
export const TOP_LEVEL_STYLE = { bold: true, fillColor: "#f2f2f2" };
export const MEASURE_STYLE = { fillColor: "#f2f2f2", textColor: "#756f6f" };
