import base64
import logging

from odoo import _, api, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10necUtils(models.AbstractModel):
    _name = "l10n_ec.utils"
    _description = "Utilities miscellaneous"

    @api.model
    def read_file(self, file, options=None):
        """
        read file from base64
        :options: data for read file, keys(encoding,separator_line,separator_field)
        :returns: [[str,str,...], [str,str,...],....]
        """
        if options is None:
            options = {}
        lines_read = []
        errors = []
        separator_line = str(options.get("separator_line", "\n"))
        separator_field = str(options.get("field_delimiter", ","))
        encoding = str(options.get("encoding", "utf-8"))
        try:
            lines_file = base64.decodebytes(file).decode(encoding).split(separator_line)
            for row in lines_file:
                line = row.split(separator_field)
                lines_read.append(line)
        except UnicodeDecodeError as er:
            raise UserError(
                _(
                    "Error to read file, please choose encoding, "
                    "Field delimiter and text delimiter right. "
                    "\n More info %s"
                )
                % tools.ustr(er)
            ) from None
        except Exception as e:
            raise UserError(
                _("Error to read file. \nMore info %s") % tools.ustr(e)
            ) from None
        return lines_read, errors
