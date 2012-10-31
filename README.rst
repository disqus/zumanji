Zumanji
=======

A web application for handling performance test results with heavy GitHub integration.

Integrates with `nose-performance <https://github.com/disqus/nose-performance>`_ to report and archive results.

See the included application in ``example/`` for information a sample setup.

.. note:: Zumanji is designed to work with GitHub, and will likely explode into a million little errors if your repo
          does not exist on GitHub.

Usage
-----

Import JSON data from your test runner::

    $ python manage.py import_performance_json <json file> --project=disqus/gargoyle

Goals
-----

Zumanji's mission is to be an extensible build reporting interface. It's primary target is improved
statistics around your tests, but may evolve into a generic build dashboard (as it has all of the
required features).

It should report things quickly and accurate, allowing to see precisely what problems may exist within
a particular build that weren't there before (whether that's a failing condition or a regression). The
system will also cater to alerting via setting trigger metrics (e.g. alert me when number of SQL calls
exceeds 15 in these tests).

Screenshots
-----------

Aggregate Report
~~~~~~~~~~~~~~~~

.. image:: https://github.com/disqus/zumanji/raw/master/screenshots/branch.png

Individual Test
~~~~~~~~~~~~~~~

.. image:: https://github.com/disqus/zumanji/raw/master/screenshots/leaf.png


Caveats
-------

This is still an evolving prototype and APIs are not stable, nor is the implementation the most efficient it could be.