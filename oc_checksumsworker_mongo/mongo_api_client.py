#!/usr/bin/env python3
import requests
import logging
import os
# something like "http://some.host.fqdn.local/part1//part2" may give an unexpected error 
# while working via http: or https:
# double-slash-speparator is OK for local *nix paths only
# and we do not guarantee there is no slash at the end of base URL while it is taken from environment or arg
# that is the cause why simply "+/part1/" is a bad idea
# we have to use some methods which guarantee one slash between parts
# 'urllib.urljoin' and 'urllib3.urljoin' have many 'features' when more than one component need to be joined
# so 'posixpath.join' seems a bit ugly, but the cheapest way
import posixpath

class MongoApiClientError(Exception):
    pass

class MongoApiClient(object):
    """
    A client for Distributives Recall API
    """
    def __init__(self, api_url=None):
        """
        :param api_url: Distributives Mongo API URL
        :type api_url: str
        """
        self.url = api_url

        if not self.url:
            self.url = os.getenv("DISTRIBUTIVES_API_URL")
  
        if not self.url:
            raise MongoApiClientError("Distributives Mongo API url was not provided.")

    def delete_location(self, location):
        """
        Delete location from DB
        :param location: str, file location (GAV for now)
        :type location: str
        """
        logging.debug(f"Deleting from the DB: {location}")
        response = requests.delete(posixpath.join(self.url, 'delete_distributive'), json={"path": location})

        if response.status_code == 200:
            logging.debug(f"Deletion success for {location}")
            return

        raise MongoApiClientError(response.text)

    def add_location(self, location, checksum, citype=None, client=None, version=None, parent=None, artifact_deliverable=None):
        """
        Register new distributive's location in the DB
        :param location: File location (GAV for now)
        :type location: str
        :param checksum: MD5 checksum
        :type checksum: str
        :param citype: distributive type
        :type citype: str
        :param version: distributive's version
        :type version: str
        :param parent: distributive's parent(s) artifact id(s)
        :type parent: list of str
        :param artifact_deliverable: is file enabled for delivery
        :type artifact_deliverable: bool
        """
        # adjust arguments
        # 'client' have to be empty string for standard distributives due to Mongo limitations
        if not client:
            client = ""

        payload = {"path": location,
                "checksum": checksum,
                "citype": citype,
                "client": client,
                "version": version}

        if parent:
            payload["parent"] = parent

        if artifact_deliverable is not None:
            payload["artifact_deliverable"] = artifact_deliverable

        logging.debug(f"Addition attempt: {payload}")
        response = requests.post(posixpath.join(self.url, "add_distributive"), json=payload)
        
        if response.status_code == 201:
            logging.debug(f"Added: {location}")
            return

        raise MongoApiClientError(response.text)
    
    def update_location(self, location, checksum, citype=None, client=None, version=None, parent=None, artifact_deliverable=None):
        """
        Register checksum for a distributive in the DB
        :param location: file location (GAV for now)
        :type location: str
        :param checksum: MD5 checksum
        :type checksum: str
        :param citype: type of distributive
        :type citype:str
        :param version: distributive's version
        :type version: str
        :param parent: distributive's parent(s) artifact id(s)
        :type parent: list of str
        :param artifact_deliverable: is file enabled for delivery
        :type artifact_deliverable: bool
        """
        # adjust arguments
        # 'client' have to be empty string for standard distributives due to Mongo limitations
        if not client:
            client = ""

        # add primary search keys to the payload
        update_payload = {"citype": citype, "version": version, "client": client, "changes": 
                {"path": location}}

        if checksum:
            update_payload["changes"]["checksum"] = checksum

        # we do not allow modification for 'artifact_deliverable' from here

        if parent:
            update_payload["changes"]["parent"] = parent

        logging.debug(f"Modification attempt: {update_payload}")
        update_response = requests.post(posixpath.join(self.url, "update_distributive"), json=update_payload)

        if update_response.status_code in [200, 201]:
            logging.debug(f"Modification success: {location}")
            return

        raise MongoApiClientError(update_response.text)
