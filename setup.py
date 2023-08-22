#!/usr/bin/env python3

from setuptools import setup
from datetime import datetime

__version = "0.1.2"

setup(name="oc-checksumsworker-mongo",
      version=__version,
      description="Checksums worker for Distributives Mongo API",
      long_description="Checksums worker for Distributives Mongo API",
      long_description_content_type="text/plain",
      install_requires=[
          "oc-checksumsq >= 10.2.3",
          "oc-cdtapi >= 3.9.5",
          "requests"
      ],

      packages=["oc_checksumsworker_mongo"],
      package_data={},
      python_requires=">=3.7",
)
