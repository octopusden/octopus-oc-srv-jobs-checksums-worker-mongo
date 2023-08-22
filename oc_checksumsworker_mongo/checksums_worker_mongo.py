#!/usr/bin/env python3
from oc_checksumsq.checksums_interface import queue_published, FileLocation, ChecksumsQueueServer
from oc_cdtapi.NexusAPI import NexusAPI, parse_gav
from .mongo_api_client import MongoApiClient, MongoApiClientError
from requests.exceptions import ConnectionError, MissingSchema
import argparse
import logging
import requests
from tempfile import TemporaryFile
import hashlib

class QueueWorkerApplicationMongo(ChecksumsQueueServer):

    def __init__(self, nexus_api=None, distributives_api_client=None, *args, **kvargs):
        self.nexus_api = nexus_api or NexusAPI()
        self.distributives_api_client = distributives_api_client or MongoApiClient()

        super().__init__(*args, **kvargs)

    def _local_md5(self, gav):
        """
        Calculate MD5 checksum locally
        :param gav: GAV
        :type gav: str
        :return: MD5 checksum, or None if not available
        """
        logging.info(f"Trying to calculate checksum of {gav} locally")
        logging.debug(f"Downloading {gav}")

        _tf = TemporaryFile()
        self.nexus_api.cat(gav, binary=True, stream=True, write_to=_tf)

        # return seek to the begin and read chunks
        # and calculate MD5 with 'hashlib'
        logging.debug(f"Calculating MD5 for {gav}")
        _tf.seek(0, 0)
        _hmd5 = hashlib.md5()

        while True:
            _chunk = _tf.read(1*1024*1024) # read 1M chunks

            if not _chunk:
                break

            _hmd5.update(_chunk)

        _tf.close()
        return _hmd5.hexdigest()

    def _checksum(self, gav):
        """
        Get checksum from MVN storage
        :param gav: GAV
        :type gav: str
        :return: MD5 checksum
        :return type: str, None
        """

        # this method is not allowed to throw any exception
        # it must simply return 'None' in case of failure
        # it should not be called if it is known artifact does not exist
        _info = None

        try:
            logging.debug(f"Attempt to get checksum for {gav}")

            # do not return directly since Nexus/Artifactory may return empty checksum
            # even if artifact exists
            # do not do all in one line also
            #      return self.nexus_api.info(gav).get("md5")
            # it looks nice, but may:
            #    1. raise unwanted exception if 'info' returns 'None'
            #       (AttributeError on NoneType object and so on)
            #    2. return illegal 'None' if empty info has been received
            # exceptions from Nexus/Artifactory are interesting only
            _info = self.nexus_api.info(gav)
        except Exception as e:
            logging.exception(e)
            pass

        if not _info:
            logging.debug(f"Empty info for {gav} from MVN")
            return self._local_md5(gav)

        _md5 = _info.get("md5")

        if not _md5:
            logging.debug(f"Empty checksum for {gav} from MVN")
            return self._local_md5(gav)

        logging.debug(f"Checksum from MVN for {gav} is {_md5}")
        return _md5

    def init(self, args):
        """
        :param args: parsed command-line arguments
        :type args: argparse namespace
        """
        self.remove = (args.remove == 'always')

    def custom_args(self, parser):
        """
        :param parser: parser of command-line arguments
        :type parser: argparse.ArgumentParser
        :return: modified parser
        :return type: argparse.ArgumentParser
        """
        parser.add_argument('--remove', help='Remove artifact from database on 404 error - no or always',
                            choices=['no', 'always'], default='no')
        return parser

    def prepare_parser(self):
        """
        Prepare command-line argument parser
        :reutrn: empty parser with description only
        :reutrn type: argparse.ArgumentParser
        """
        return argparse.ArgumentParser(description='Checksums queue worker with Distributives Mongo API support')

    def _register_distributive(self, gav, checksum, citype, client=None, version=None, parent=None, artifact_deliverable=None, remove=False):
        """
        Common registration activity
        :param gav: GAV
        :type gav: str
        :param checksum: checksum
        :type checksum: str
        :param citype: type
        :type citype: str
        :param client: CDT client code
        :type client: str
        :parram version: version
        :type version: str
        :param parent: parent distributives
        :type parent: list of str
        :param artifact_deliverable: allowed for delivery or not
        :type artifact_deliverable: bool
        :param remove: perform distributive removing if not exist
        :type remove: bool
        """

        #   we need client and version for primary key in Distributives database
        #   if not provided - we are trying to parse them from GAV
        try:
            _gav = parse_gav(gav)
        except (ValueError, TypeError, KeyError) as _e:
            logging.info(f"Not MVN distributive: '{gav}': {type(_e)}: {_e}")
            return

        # NOTE: added 'version' pasing
        #       here we want to raise an exception if version is absent, so not using safe 'get' method
        #       like this:
        #       version = parse_gav(gav).get('v')
        # NOTE 2: here we have to parse client code, ci_type and version from GAV in the future
        if not version:
            logging.debug(f"Assigning version from {gav}")
            version = _gav['v']

        #   we are silently ignoring messages with incomplete data
        #   we are silently ignoring non-distributives also
        if any([not citype,
                not version,
                not client and citype and citype.endswith("CLIENT"),
                citype and "DSTR" not in citype]):
            logging.warning(f"Ignoring incomplete or invalid data: gav='{gav}', citype='{citype}', version='{version}', client='{client}'")
            return

        # delete artifact if it does not exist
        # (if allowed)
        if not self.nexus_api.exists(gav):
            logging.info(f"File {gav} does not exist")

            if remove:
                # we do not want to fail here if something goes wrong
                # just log an exception
                logging.info(f"Deleting: '{gav}'")
                try:
                    self.distributives_api_client.delete_location(gav)
                except Exception as e:
                    logging.error(f"Deletion failed: '{gav}'", exc_info=True)
                    pass

            return

        # added checksum obtaining
        if not checksum:
            checksum = self._checksum(gav)

        # try to modify existent location first
        # use fields allowed for modification only
        # 'MongoApiError' is OK here (nonexistent distributive), catch it
        # stop processing on successful modification
        try:
            logging.debug(f"Trying update existing '{gav}'")
            self.distributives_api_client.update_location(gav, checksum, citype, client, version, parent, artifact_deliverable)
            return
        except MongoApiClientError as e:
            logging.debug(f"Updating failed: '{gav}', error: {e}")
            pass

        # try to add new location
        # here we want to raise an exception in case of failure, so do not catch any
        # logging of those exceptions is implemented in base class,
        # not necessary to do it here again
        self.distributives_api_client.add_location(gav, checksum, citype, client, version, parent, artifact_deliverable)
        return

    def ping(self):
        """
        Ping response
        """
        return

    def register_file(self, location, citype, depth=0, remove=False, version=None, client=None, parent=None, artifact_deliverable=None):
        """
        Register file in DB using Distributives Mongo API
        :param location: File location
        :type location: FileLocation(path, location_type, revision)
        :param citype: object's citype
        :type citype: str
        :param depth: registration depth (used here for backwards-compatibility only)
        :type depth: any
        :param remove: if 'True' - distributive will be deleted if not exists in MVN
        :type remove: bool
        :param version: distributive's version
        :type version: str
        :param client: CDT client code
        :type client: str
        :param parent: distributive's parent(s) artifact id(s)
        :type parent: list of str
        :param artifact_deliverable: is the file enabled for client delivery
        :type artifact_deliverable: bool
        """
        location_gav = FileLocation(*location).path
        logging.info(f"Received registration request for path {location_gav}")

        # the rest part is similar for both "register_file" and "register_checksum" within new concept
        return self._register_distributive(
                gav=location_gav,
                checksum=None,
                citype=citype,
                version=version,
                client=client,
                parent=parent,
                artifact_deliverable=artifact_deliverable,
                remove=(remove or self.remove))

    def register_checksum(self, location, checksum, citype=None, cs_prov='Regular', mime='Data', cs_alg='MD5', version=None, client=None, parent=None, artifact_deliverable=None):
        """
        Register checksum for distributive in DB
        :param location: File location
        :type location: FileLocation(path, location_type, revision)
        :param checksum: checksum
        :type checksum: str
        :param citype: object's citype
        :type citype: str
        :param cs_prov: checksums's provider (used here for backwards-compatibility only)
        :type cs_prov: any
        :param mime: MIME type (used here for backwards-compatibility only)
        :type mime: any
        :param cs_alg: checksum algorithm, only MD5 is supported for the time being
        :type cs_alg: any
        :param version: distributive's version
        :type version: str
        :param client: CDT client code
        :type client: str
        :param parent: distributive's parent(s) artifact id(s)
        :type parent: list of str
        :param artifact_deliverable: is the file enabled for client delivery
        :type artifact_deliverable: bool
        """
        location_gav = FileLocation(*location).path
        logging.info(f"Registering checksum {checksum} for {location_gav}")

        if cs_alg != 'MD5':
            raise NotImplementedError('MD5 checksum is supported only')

        # the rest part is similar for both "register_file" and "register_checksum" within new concept
        return self._register_distributive(
                gav=location_gav,
                checksum=checksum,
                citype=citype,
                version=version,
                client=client,
                parent=parent,
                artifact_deliverable=artifact_deliverable,
                remove=False)

if __name__ == '__main__':
    exit(QueueWorkerApplicationMongo().main())
