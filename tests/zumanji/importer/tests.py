from datetime import datetime
from django.test import TestCase
from zumanji.importer import convert_timestamp


class ConvertTimestampTest(TestCase):
    def test_basic(self):
        result = convert_timestamp('2012-05-16T03:43:59.23')
        self.assertEquals(result, datetime(2012, 5, 16, 3, 43, 59, 230000))
