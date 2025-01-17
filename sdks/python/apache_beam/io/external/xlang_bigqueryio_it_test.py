#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Unit tests for cross-language BigQuery sources and sinks."""
# pytype: skip-file

import datetime
import logging
import os
import secrets
import time
import unittest
from decimal import Decimal

import pytest
from hamcrest.core import assert_that as hamcrest_assert

import apache_beam as beam
from apache_beam.io.gcp.bigquery import StorageWriteToBigQuery
from apache_beam.io.gcp.bigquery_tools import BigQueryWrapper
from apache_beam.io.gcp.internal.clients import bigquery
from apache_beam.io.gcp.tests.bigquery_matcher import BigqueryFullResultMatcher
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.utils.timestamp import Timestamp

# Protect against environments where bigquery library is not available.
# pylint: disable=wrong-import-order, wrong-import-position

try:
  from apitools.base.py.exceptions import HttpError
except ImportError:
  HttpError = None
# pylint: enable=wrong-import-order, wrong-import-position

_LOGGER = logging.getLogger(__name__)


@pytest.mark.uses_gcp_java_expansion_service
@unittest.skipUnless(
    os.environ.get('EXPANSION_PORT'),
    "EXPANSION_PORT environment var is not provided.")
class BigQueryXlangStorageWriteIT(unittest.TestCase):
  BIGQUERY_DATASET = 'python_xlang_storage_write'

  ELEMENTS = [
      # (int, float, numeric, string, bool, bytes, timestamp)
      {
          "int": 1,
          "float": 0.1,
          "numeric": Decimal("1.11"),
          "str": "a",
          "bool": True,
          "bytes": b'a',
          "timestamp": Timestamp(1000, 100)
      },
      {
          "int": 2,
          "float": 0.2,
          "numeric": Decimal("2.22"),
          "str": "b",
          "bool": False,
          "bytes": b'b',
          "timestamp": Timestamp(2000, 200)
      },
      {
          "int": 3,
          "float": 0.3,
          "numeric": Decimal("3.33"),
          "str": "c",
          "bool": True,
          "bytes": b'd',
          "timestamp": Timestamp(3000, 300)
      },
      {
          "int": 4,
          "float": 0.4,
          "numeric": Decimal("4.44"),
          "str": "d",
          "bool": False,
          "bytes": b'd',
          "timestamp": Timestamp(4000, 400)
      }
  ]

  def setUp(self):
    self.test_pipeline = TestPipeline(is_integration_test=True)
    self.args = self.test_pipeline.get_full_options_as_args()
    self.project = self.test_pipeline.get_option('project')

    self.bigquery_client = BigQueryWrapper()
    self.dataset_id = '%s%s%s' % (
        self.BIGQUERY_DATASET, str(int(time.time())), secrets.token_hex(3))
    self.bigquery_client.get_or_create_dataset(self.project, self.dataset_id)
    _LOGGER.info(
        "Created dataset %s in project %s", self.dataset_id, self.project)

    _LOGGER.info("expansion port: %s", os.environ.get('EXPANSION_PORT'))
    self.expansion_service = ('localhost:%s' % os.environ.get('EXPANSION_PORT'))

  def tearDown(self):
    request = bigquery.BigqueryDatasetsDeleteRequest(
        projectId=self.project, datasetId=self.dataset_id, deleteContents=True)
    try:
      _LOGGER.info(
          "Deleting dataset %s in project %s", self.dataset_id, self.project)
      self.bigquery_client.client.datasets.Delete(request)
    except HttpError:
      _LOGGER.debug(
          'Failed to clean up dataset %s in project %s',
          self.dataset_id,
          self.project)

  def parse_expected_data(self, expected_elements):
    data = []
    for row in expected_elements:
      values = list(row.values())
      for i, val in enumerate(values):
        if isinstance(val, Timestamp):
          # BigQuery matcher query returns a datetime.datetime object
          values[i] = val.to_utc_datetime().replace(
              tzinfo=datetime.timezone.utc)
      data.append(tuple(values))

    return data

  def storage_write_test(self, table_name, items, schema):
    table_id = '{}:{}.{}'.format(self.project, self.dataset_id, table_name)

    bq_matcher = BigqueryFullResultMatcher(
        project=self.project,
        query="SELECT * FROM %s" % '{}.{}'.format(self.dataset_id, table_name),
        data=self.parse_expected_data(items))

    with beam.Pipeline(argv=self.args) as p:
      _ = (
          p
          | beam.Create(items)
          | beam.io.WriteToBigQuery(
              table=table_id,
              method=beam.io.WriteToBigQuery.Method.STORAGE_WRITE_API,
              schema=schema,
              expansion_service=self.expansion_service))
    hamcrest_assert(p, bq_matcher)

  def test_storage_write_all_types(self):
    table_name = "python_storage_write_all_types"
    schema = (
        "int:INTEGER,float:FLOAT,numeric:NUMERIC,str:STRING,"
        "bool:BOOLEAN,bytes:BYTES,timestamp:TIMESTAMP")
    self.storage_write_test(table_name, self.ELEMENTS, schema)

  def test_storage_write_nested_records_and_lists(self):
    table_name = "python_storage_write_nested_records_and_lists"
    schema = {
        "fields": [{
            "name": "repeated_int", "type": "INTEGER", "mode": "REPEATED"
        },
                   {
                       "name": "struct",
                       "type": "STRUCT",
                       "fields": [{
                           "name": "nested_int", "type": "INTEGER"
                       }, {
                           "name": "nested_str", "type": "STRING"
                       }]
                   },
                   {
                       "name": "repeated_struct",
                       "type": "STRUCT",
                       "mode": "REPEATED",
                       "fields": [{
                           "name": "nested_numeric", "type": "NUMERIC"
                       }, {
                           "name": "nested_bytes", "type": "BYTES"
                       }]
                   }]
    }
    items = [{
        "repeated_int": [1, 2, 3],
        "struct": {
            "nested_int": 1, "nested_str": "a"
        },
        "repeated_struct": [{
            "nested_numeric": Decimal("1.23"), "nested_bytes": b'a'
        },
                            {
                                "nested_numeric": Decimal("3.21"),
                                "nested_bytes": b'aa'
                            }]
    }]

    self.storage_write_test(table_name, items, schema)

  def test_storage_write_beam_rows(self):
    table_id = '{}:{}.python_xlang_storage_write_beam_rows'.format(
        self.project, self.dataset_id)

    row_elements = [
        beam.Row(
            my_int=e['int'],
            my_float=e['float'],
            my_numeric=e['numeric'],
            my_string=e['str'],
            my_bool=e['bool'],
            my_bytes=e['bytes'],
            my_timestamp=e['timestamp']) for e in self.ELEMENTS
    ]

    bq_matcher = BigqueryFullResultMatcher(
        project=self.project,
        query="SELECT * FROM %s" %
        '{}.python_xlang_storage_write_beam_rows'.format(self.dataset_id),
        data=self.parse_expected_data(self.ELEMENTS))

    with beam.Pipeline(argv=self.args) as p:
      _ = (
          p
          | beam.Create(row_elements)
          | StorageWriteToBigQuery(
              table=table_id, expansion_service=self.expansion_service))
    hamcrest_assert(p, bq_matcher)


if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  unittest.main()
