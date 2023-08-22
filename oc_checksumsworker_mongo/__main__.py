#!/usr/bin/env python3
from .checksums_worker_mongo import QueueWorkerApplicationMongo

if __name__ == '__main__':
    exit(QueueWorkerApplicationMongo().main())
