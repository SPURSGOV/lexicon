===============
Developer guide
===============

Thanks! There are tons of different DNS services, and unfortunately a large portion of them require
paid accounts, which makes it hard for us to develop ``lexicon`` providers on our own. We want to keep
it as easy as possible to contribute to ``lexicon``, so that you can automate your favorite DNS service.
There are a few guidelines that we need contributors to follow so that we can keep on top of things.

Setup a development environment
===============================

Fork, then clone the repo:

.. code-block:: bash

    git clone git@github.com:your-username/lexicon.git

Install Poetry if you not have it already:

.. code-block:: bash

    # On Linux / WSL2
    curl -sSL https://install.python-poetry.org | python3 -

.. code-block:: powershell

    # On Windows (powershell)
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

Configure the virtual environment with full providers support:

.. code-block:: bash

    cd lexicon
    poetry install -E full

Activate the virtual environment

.. code-block:: bash

    # On Linux / WSL2
    source .venv/bin/activate

.. code-block:: powershell

    # On Windows (powershell)
    ./.venv/Scripts/activate

Make sure all tests pass:

.. code-block:: bash

    tox -e py

You can test a specific provider using:

.. code-block:: bash

    pytest lexicon/tests/providers/test_foo.py

.. note::

    Please note that by default, tests are replayed from recordings located in
    ``tests/fixtures/cassettes``, not against the real DNS provider APIs.

Adding a new DNS provider
=========================

Now that you have a working development environment, let's add a new provider.
Internally lexicon does a bit of magic to wire everything together, so you need to create
the following Python module where all the code for your provider will settle.

 - ``lexicon/providers/foo.py``

Where ``foo`` should be replaced with the name of the DNS service in lowercase
and without spaces or special characters (eg. ``cloudflare``).

Your provider module **must** contain a class named ``Provider`` inheriting from BaseProvider_
(defined in  ``base.py`` file). This class **must** implements the following abstract methods
defined by BaseProvider_:

  - ``_authenticate``
  - ``_create_record``
  - ``_list_records``
  - ``_update_record``
  - ``_delete_record``
  - ``_request``
  - ``get_nameservers`` (static method)
  - ``configure_parser`` (static method)

You should review the `provider conventions`_ to ensure that ``_authenticate`` and ``*_record(s)``
methods follow the proper behavior and API contracts.

The static method ``get_nameservers`` returns the list of FQDNs of the nameservers used by
the DNS provider. For instance, Google Cloud DNS uses nameservers that have the FQDN pattern
``ns-cloud-cX-googledomains.com``, so ``get_nameservers`` will return ``['googledomains.com']``
in this case.

The static method ``configure_parser`` is called to add the provider specific commandline arguments.
For instance, if you define two cli arguments: ``--auth-username`` and ``--auth-token``, those
values will be available to your provider via ``self._get_provider_option('auth_username')``
or ``self._get_provider_option('auth_token')`` respectively.

.. note::

    Several important notes:

    - ``lexicon`` is designed to work with multiple versions of python. That means
      your code will be tested against python 3.8 and 3.11 on Windows, Linux and Mac OS X.
    - any provider specific dependencies need a particular configuration in the ``pyproject.toml``
      file:

    Under the ``[tool.poetry.dependencies]`` block, add the specific dependency
    as an optional dependency.

    .. code-block:: toml

        [tool.poetry.dependencies]
        # Optional dependencies required by some providers
        additionalpackage = { version = "*", optional = true }  # mycustomprovider

    Under the ``[tool.poetry.extras]`` block, define a new extra group named after the provider name
    requiring the optional dependency, then add this extra group inside the ``full`` group.

    .. code-block:: toml

        [tool.poetry.extras]
        mycustomprovider = ["additionalpackage"]
        full = [..., "mycustomprovider"]

.. _BaseProvider: https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py
.. _cloudflare.py: https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/cloudflare.py
.. _lexicon/providers/: https://github.com/AnalogJ/lexicon/tree/master/lexicon/providers
.. _provider conventions: https://dns-lexicon.readthedocs.io/en/latest/provider_conventions.html

Testing your provider
=====================

Static code analysis
--------------------

The project codebase is checked by a linter (flake8) and against types declaration (mypy). Both
analysis must pass. You can run them with the following command:

.. code-block:: bash

    tox -e lint
    tox -e mypy

Test against the live API
-------------------------

First let's validate that your provider shows up in the CLI.

.. code-block:: bash

    lexicon foo --help

If everything worked correctly, you should get a help page that's specific
to your provider, including your custom optional arguments.

Now you can run some manual commands against your provider to verify that
everything works as you expect.

.. code-block:: bash

    lexicon foo list example.com TXT
    lexicon foo create example.com TXT --name demo --content "fake content"

Once you're satisfied that your provider is working correctly, we'll run the
integration test suite against it, and verify that your provider responds the
same as all other ``lexicon`` providers. ``lexicon`` uses ``vcrpy`` to make recordings
of actual HTTP requests against your DNS service's API, and then reuses those
recordings during testing.

The only thing you need to do is create the following file:

 - ``lexicon/tests/providers/test_foo.py``

Then you'll need to populate it with the following template:

.. code-block:: python

    # Test for one implementation of the interface
    from lexicon.tests.providers.integration_tests import IntegrationTestsV2
    from unittest import TestCase

    # Hook into testing framework by inheriting unittest.TestCase and reuse
    # the tests which *each and every* implementation of the interface must
    # pass, by inheritance from integration_tests.IntegrationTests
    class FooProviderTests(TestCase, IntegrationTestsV2):
        """Integration tests for Foo provider"""
        provider_name = 'foo'
        domain = 'example.com'
        def _filter_post_data_parameters(self):
            return ['login_token']

        def _filter_headers(self):
            return ['Authorization']

        def _filter_query_parameters(self):
            return ['secret_key']

        def _filter_response(self, response):
            """See `IntegrationTests._filter_response` for more information on how
            to filter the provider response."""
            return response

Make sure to replace any instance of ``foo`` or ``Foo`` with your provider name.
``domain`` should be a real domain registered with your provider (some providers
have a sandbox/test environment which doesn't require you to validate ownership).

The ``_filter_*`` methods ensure that your credentials are not included in the
``vcrpy`` recordings that are created. You can take a look at recordings for other
providers, they are stored in the `tests/fixtures/cassettes/`_ sub-folders.

Then you'll need to setup your environment variables for testing. Unlike running
``lexicon`` via the CLI, the test suite cannot take user input, so we'll need to provide
any CLI arguments containing secrets (like ``--auth-*``) using environmental variables
prefixed with ``LEXICON_FOO_``.

For instance, if you had a ``--auth-token`` CLI argument, you can populate it
using the ``LEXICON_FOO_AUTH_TOKEN`` environmental variable.

Notice also that you should pass any required non-secrets arguments programmatically using the
``_test_parameters_override()`` method. See `test_powerdns.py`_ for an example.

.. _tests/fixtures/cassettes/: https://github.com/AnalogJ/lexicon/tree/master/tests/fixtures/cassettes
.. _test_powerdns.py: https://github.com/AnalogJ/lexicon/blob/5ee4d16f9d6206e212c2197f2e53a1db248f5eb9/lexicon/tests/providers/test_powerdns.py#L19

Add new tests recordings
------------------------

Now you need to run the ``py.test`` suite again, but in a different mode: the live tests mode.
In default test mode, tests are replayed from existing recordings. In live mode, tests are executed
against the real DNS provider API, and recordings will automatically be generated for your provider.

To execute the ``py.test`` suite using the live tests mode, execute py.test with the environment
variable ``LEXICON_LIVE_TESTS`` set to ``true`` like below:

.. code-block:: bash

	LEXICON_LIVE_TESTS=true pytest lexicon/tests/providers/test_foo.py

If any of the integration tests fail on your provider, you'll need to delete the recordings that
were created, make your changes and then try again.

.. code-block:: bash

    rm -rf tests/fixtures/cassettes/foo/IntegrationTests

Once all your tests pass, you'll want to double check that there is no sensitive data in the
``tests/fixtures/cassettes/foo/IntegrationTests`` folder, and then ``git add`` the whole folder.

.. code-block:: bash

    git add tests/fixtures/cassettes/foo/IntegrationTests

Finally, push your changes to your Github fork, and open a PR.

Skipping some tests
-------------------

Neither of the snippets below should be used unless necessary. They are only included
in the interest of documentation.

In your ``lexicon/tests/providers/test_foo.py`` file, you can use ``@pytest.mark.skip`` to skip
any individual test that does not apply (and will never pass)

.. code-block:: python

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

You can also skip extended test suites by inheriting your provider test class from ``IntegrationTestsV1``
instead of ``IntegrationTestsV2``:

.. code-block:: python

    from lexicon.tests.providers.integration_tests import IntegrationTestsV1
    from unittest import TestCase

    class FooProviderTests(TestCase, IntegrationTestsV1):
        """Integration tests for Foo provider"""

CODEOWNERS file
===============

Finally you should add yourself to the `CODEOWNERS file`_, in the root of the repo.
It's my way of keeping track of who to ping when I need updated recordings as the
test suites expand & change.

.. _CODEOWNERS file: https://github.com/AnalogJ/lexicon/blob/master/CODEOWNERS
