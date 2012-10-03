try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('zumanji').version
except Exception, e:
    VERSION = 'unknown'
