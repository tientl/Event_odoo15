# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import logging
import zipfile
import requests
from requests.exceptions import RequestException
from lxml import etree, objectify

from odoo import models
from odoo.tools import xml_utils
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _l10n_pe_edi_load_xsd_attachments(self):
        # This method only brings the xsd files if it doesn't exist as attachment
        url = 'http://cpe.sunat.gob.pe/sites/default/files/inline-files/XSD%202.1.zip'
        _logger.info('Downloading file from sunat: %s', url)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except RequestException as error:
            _logger.warning('Connection error %s with the given URL: %s', error, url)
            return

        try:
            archive = zipfile.ZipFile(io.BytesIO(response.content))
        except Exception:
            _logger.warning('UNZIP for XSD failed from URL: %s', url)
            return
        for file_path in archive.namelist():
            _, file_name = file_path.rsplit('/', 1)
            if not file_name:
                continue

            attachment = self.env.ref('l10n_pe_edi.%s' % file_name, False)
            if attachment:
                continue

            content = archive.read(file_path)
            try:
                content = content.replace(b'schemaLocation="../common/', b'schemaLocation="')
                xsd_object = objectify.fromstring(content)
            except etree.XMLSyntaxError as e:
                _logger.warning('You are trying to load an invalid xsd file.\n%s', e)
                return
            validated_content = etree.tostring(xsd_object, pretty_print=True)
            attachment = self.create({
                'name': file_name,
                'description': file_path,
                'datas': base64.encodebytes(validated_content),
                'company_id': False,
            })
            self.env['ir.model.data'].create({
                'name': file_name,
                'module': 'l10n_pe_edi',
                'res_id': attachment.id,
                'model': 'ir.attachment',
                'noupdate': True,
            })

    def _l10n_pe_edi_check_with_xsd(self, xml_to_validate, validation_type):
        """
        This method validates the format description of the xml files

        :param xml_to_validate: xml to validate
        :param validation_type: the type of the document
        :return: empty string when file not found or XSD passes
         or the error when the XSD validation fails
        """
        validation_types = self._l10n_pe_edi_get_xsd_file_name()
        xsd_fname = validation_types[validation_type]
        try:
            xml_utils._check_with_xsd(xml_to_validate, xsd_fname, self.sudo().env)
            return ''
        except FileNotFoundError:
            _logger.info('The XSD validation files from Sunat has not been found, please run the cron manually. ')
            return ''
        except UserError as exc:
            return str(exc)

    def _l10n_pe_edi_get_xsd_file_name(self):
        return {
            '01': 'UBL-Invoice-2.1.xsd',
            '03': 'UBL-Invoice-2.1.xsd',
            '07': 'UBL-CreditNote-2.1.xsd',
            '08': 'UBL-DebitNote-2.1.xsd',
        }
