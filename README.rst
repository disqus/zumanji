Zumanji
=======

A web application for handling performance test results.

Integrates with `nose-performance <https://github.com/disqus/nose-performance>`_ to report and archive results.

See the included application in ``example/`` for information a sample setup.

Usage
-----

Import JSON data from your test runner::

    $ python manage.py import_performance_json <json file> --project=disqus-web

Screenshots
-----------

.. image:: https://github.com/disqus/zumanji/raw/master/screenshots/branch.png

.. image:: https://github.com/disqus/zumanji/raw/master/screenshots/leaf.png
