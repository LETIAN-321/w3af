"""
error_500.py

Copyright 2006 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import w3af.core.data.kb.knowledge_base as kb
import w3af.core.data.constants.severity as severity

from w3af.core.controllers.plugins.grep_plugin import GrepPlugin
from w3af.core.data.db.disk_set import DiskSet
from w3af.core.data.kb.vuln import Vuln


class error_500(GrepPlugin):
    """
    Grep every page for error 500 pages that haven't been identified as bugs by
    other plugins.

    :author: Andres Riancho (andres.riancho@gmail.com)
    """

    IGNORE_CODES = (404, 403, 401, 405, 400, 501)
    FALSE_POSITIVE_STRINGS = ('<h1>Bad Request (Invalid URL)</h1>',
                              )

    def __init__(self):
        GrepPlugin.__init__(self)

        self._error_500_responses = DiskSet(table_prefix='error_500')

    def grep(self, request, response):
        """
        Plugin entry point, identify which requests generated a 500 error.

        :param request: The HTTP request object.
        :param response: The HTTP response object
        :return: None
        """
        if response.is_text_or_html() \
        and 400 < response.get_code() < 600 \
        and response.get_code() not in self.IGNORE_CODES\
        and not self._is_false_positive(response):
            self._error_500_responses.add((request, response.id))

    def _is_false_positive(self, response):
        """
        Filters out some false positives like this one:

        This false positive is generated by IIS when I send an URL that's "odd"
        Some examples of URLs that trigger this false positive:
            - http://127.0.0.2/ext.ini.%00.txt
            - http://127.0.0.2/%00/
            - http://127.0.0.2/%0a%0a<script>alert(\Vulnerable\)</script>.jsp

        :return: True if the response is a false positive.
        """
        for fps in self.FALSE_POSITIVE_STRINGS:
            if fps in response.get_body():
                return True
        return False

    def end(self):
        """
        This method is called when the plugin wont be used anymore.

        The real job of this plugin is done here, where I will try to see if
        one of the error_500 responses were not identified as a vuln by some
        of my audit plugins
        """
        all_vuln_ids = set()

        for vuln in kb.kb.get_all_vulns():
            for _id in vuln.get_id():
                all_vuln_ids.add(_id)

        for request, error_500_response_id in self._error_500_responses:

            if error_500_response_id not in all_vuln_ids:
                # Found a error 500 that wasn't identified !
                desc = 'An unidentified web application error (HTTP response'\
                       ' code 500) was found at: "%s". Enable all plugins and'\
                       ' try again, if the vulnerability still is not'\
                       ' identified, please verify manually and report it to'\
                       ' the w3af developers.'
                desc = desc % request.get_url()

                v = Vuln('Unhandled error in web application', desc,
                         severity.MEDIUM, error_500_response_id,
                         self.get_name())

                v.set_uri(request.get_uri())

                self.kb_append_uniq(self, 'error_500', v, 'VAR')

        self._error_500_responses.cleanup()

    def get_long_desc(self):
        """
        :return: A DETAILED description of the plugin functions and features.
        """
        return """
        This plugin greps every page for error 500 pages that have'nt been caught
        by other plugins. By enabling this, you are enabling a "safety net" that
        will catch all interesting HTTP responses which might lead to a bug or
        vulnerability.
        """
