# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import requests
from lxml import etree, objectify

from odoo import models

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _load_xsd_lu_electronic_files(self):
        """
        Loads XSD file for checking LU electronic XML reports. Allows to check that the generated reports are in the
        right XML schema before exporting them.
        """
        attachment = self.env.ref('l10n_lu_reports.xsd_cached_eCDF_file_v2_0-XML_schema_xsd', False)
        if attachment:
            return
        try:
            response = requests.get('https://ecdf-developer.b2g.etat.lu/ecdf/formdocs/eCDF_file_v2.0-XML_schema.xsd', timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.info('Cannot connect with the given URL for the Luxembourg electronic reports xsd.')
            return
        try:
            objectify.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            _logger.info('You are trying to load an invalid xsd file for the Luxembourg electronic reports.\n%s', e)
            return
        attachment = self.create({
            'name': 'xsd_cached_eCDF_file_v2_0-XML_schema_xsd',
            # removing \P{Cc} character class because it seems to pose trouble in the validation, even for valid files
            'datas': base64.encodebytes(response.content.replace(b'<xsd:pattern value="[\\P{Cc}]+" />', b'')),
        })
        self.env['ir.model.data'].create({
            'name': 'xsd_cached_eCDF_file_v2_0-XML_schema_xsd',
            'module': 'l10n_lu_reports',
            'res_id': attachment.id,
            'model': 'ir.attachment',
            'noupdate': True
        })
        return True


    def _modify_and_validate_xsd_content(self, module_name, content):
        xsd_object = super()._modify_and_validate_xsd_content(module_name, content)
        if len(xsd_object) == 0 or module_name != 'l10n_lu_report':
            return xsd_object
        # Luxembourg government does not accept FAIA files without `xmlns` attribute for
        # it's root element, which is, `xs:schema`. And the XSD file available on their
        # portal itself does not have this attribute. Furthermore, they refused to update
        # the file with the said attribute on their portal. So, we are using below hack to
        # set `xmlns` attribute in the XSD file after we downloaded from their portal. This
        # will ensure `xmlns` attribute's presence by validating FAIA XML with XSD using
        # tools.xml_utils._check_with_xsd() call.
        [tree] = xsd_object.xpath('//xs:schema', namespaces={'xs': 'http://www.w3.org/2001/XMLSchema'})
        if 'xmlns' not in tree.attrib:
            tree.attrib['xmlns'] = "urn:OECD:StandardAuditFile-Taxation/2.00"
        if 'targetNamespace' not in tree.attrib:
            tree.attrib['targetNamespace'] = "urn:OECD:StandardAuditFile-Taxation/2.00"
        return xsd_object
