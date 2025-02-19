# Test for one implementation of the interface
import json
import re
import urllib.parse
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class WedosProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for wedos provider"""

    provider_name = "wedos"
    domain = "kaniok.com"

    def _filter_request(self, request):
        request_start_string = "request="
        try:
            body = urllib.parse.unquote_plus(
                urllib.parse.unquote(request.body.decode())
            )
            body = re.sub(r"request=", "", body)
            data = json.loads(body)
        except ValueError:
            pass
        else:
            data["request"]["user"] = "username"
            data["request"]["auth"] = "password"
            body = request_start_string + json.dumps(data)
            body = urllib.parse.quote(urllib.parse.quote_plus(body.encode()))
            request.body = body

        return request
