from unittest import mock, TestCase
from .mocks import NexusAPIMock, QueueWorkerApplicationMock, MockResponse
from ..mongo_api_client import MongoApiClient, MongoApiClientError
from oc_checksumsq.checksums_interface import ChecksumsQueueClient, FileLocation
from oc_cdt_queue2.test.synchron.mocks.queue_loopback import LoopbackConnection, global_messaging, global_message_queue
import posixpath
from tempfile import TemporaryFile
import hashlib

import logging
logging.getLogger().propagate = False
logging.getLogger().disabled = True

class QueueWorkerApplicationMongoTest(TestCase):
    def setUp(self):
        self.app = QueueWorkerApplicationMock(nexus_api=NexusAPIMock(), distributives_api_client=MongoApiClient(api_url="http://distro-api-test"))
        self.rpc = ChecksumsQueueClient()
        self.app.remove = None

        self.rpc._Connection = LoopbackConnection
        self.app._Connection = LoopbackConnection

        self.rpc.setup('amqp://127.0.0.1/', queue='test')
        self.rpc.connect()
        self.app.main('--queue test --declare only --amqp-url amqp://127.0.0.1/'.split(' '))

        self.app.max_sleep = 0
    
    def connect_to_queue_and_check_messages(self, msg_count=1, good_msg_count=1, bad_msg_count=0):
        self.app.main('--queue test --amqp-url amqp://127.0.0.1/'.split(' '))
        self.assertEqual(self.app.counter_messages, msg_count)
        self.assertEqual(self.app.counter_good, good_msg_count)
        self.assertEqual(self.app.counter_bad, bad_msg_count)
    
    def test_rpc_ping(self):
        self.rpc.ping()
        self.connect_to_queue_and_check_messages()


    ### FILE REG
    @mock.patch('requests.post')
    def test_rpc_register_add_file__standard(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, citype="TESTDSTR", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "parent": [ "gg6:aa6:vv6:pp6" ],
            "client": "", "path": "gg:aa:vv:pp",
            "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})
    
    @mock.patch('requests.post')
    def test_rpc_register_add_file__customer(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, "TESTDSTRCLIENT", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"], client="TEST_CLIENT")
        self.connect_to_queue_and_check_messages()
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTRCLIENT", "version": "1.01", "parent": [ "gg6:aa6:vv6:pp6" ], "client": "TEST_CLIENT", "path": "gg:aa:vv:pp",
            "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTRCLIENT", "version": "1.01", "client": "TEST_CLIENT", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})

    @mock.patch('requests.post')
    def test_rpc_register_add_file__customer_not_set(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, "TESTDSTRCLIENT", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        rqmock.assert_not_called()

    @mock.patch('requests.post')
    def test_rpc_register_add_file__not_enough_data(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, None, remove=True)
        self.connect_to_queue_and_check_messages()
        rqmock.assert_not_called()

    # the same but update succoess
    @mock.patch('requests.post')
    def test_rpc_register_update_file__standard(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "update_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, citype="TESTDSTR", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        rqmock.assert_called_once_with("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})
    
    @mock.patch('requests.post')
    def test_rpc_register_update_file__customer(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "update_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, "TESTDSTRCLIENT", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"], client="TEST_CLIENT")
        self.connect_to_queue_and_check_messages()
        rqmock.assert_called_once_with("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTRCLIENT", "version": "1.01", "client": "TEST_CLIENT", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})


    def _md5(self, fl):
        _hmd5 = hashlib.md5()

        while True:
            _chunk = fl.read(1*1024*1024) # read 1M chunks

            if not _chunk:
                break

            _hmd5.update(_chunk)

        return _hmd5.hexdigest()
        

    # the same but calculate checksum on our side
    @mock.patch('requests.post')
    def test_rpc_register_add_file__no_checksum(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("this.is.trash.without.md5:bullshit:x.x.x:pkg", "NXS", 1)
        self.assertIsNone(NexusAPIMock().info("this.is.trash.without.md5:bullshit:x.x.x:pkg").get("md5"))
        _tempfile = TemporaryFile()
        NexusAPIMock().cat("this.is.trash.without.md5:bullshit:x.x.x:pkg", write_to=_tempfile)
        _tempfile.seek(0, 0)
        _md5 = self._md5(_tempfile)
        _tempfile.close()
        self.rpc.register_file(location, citype="TESTDSTR", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTR",
            "version": "1.01",
            "parent": [ "gg6:aa6:vv6:pp6" ],
            "client": "",
            "path": "this.is.trash.without.md5:bullshit:x.x.x:pkg",
            "checksum": _md5})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "this.is.trash.without.md5:bullshit:x.x.x:pkg",
                "checksum": _md5}})
    
    @mock.patch('requests.post')
    def test_rpc_register_update_file__no_checksum(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "update_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("this.is.trash.without.md5:bullshit:x.x.x:pkg", "NXS", 1)
        self.assertIsNone(NexusAPIMock().info("this.is.trash.without.md5:bullshit:x.x.x:pkg").get("md5"))
        _tempfile = TemporaryFile()
        NexusAPIMock().cat("this.is.trash.without.md5:bullshit:x.x.x:pkg", write_to=_tempfile)
        _tempfile.seek(0, 0)
        _md5 = self._md5(_tempfile)
        _tempfile.close()
        self.rpc.register_file(location, citype="TESTDSTR", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        self.assertEqual(rqmock.call_count, 1)
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "this.is.trash.without.md5:bullshit:x.x.x:pkg",
                "checksum": _md5}})
    

    # registration fail
    @mock.patch('requests.post')
    def test_rpc_register_file_fail(self, rqmock):
        def _retval(*args, **kwargs):
            return MockResponse(409, "Conflict")

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_file(location, citype="TESTDSTR", remove=True, version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages(1, 0, 1)
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTR",
            "version": "1.01",
            "parent": [ "gg6:aa6:vv6:pp6" ],
            "client": "",
            "path": "gg:aa:vv:pp",
            "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum":  NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})

    ### CHECKSUM REG
    @mock.patch('requests.post')
    def test_rpc_register_add_checksum__standard(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"),
                citype="TESTDSTR", version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "parent": [ "gg6:aa6:vv6:pp6" ], "client": "", "path": "gg:aa:vv:pp",
            "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})
    
    @mock.patch('requests.post')
    def test_rpc_register_add_checksum__customer(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"),
                citype="TESTDSTRCLIENT", version="1.01", parent=["gg6:aa6:vv6:pp6"], client="TEST_CLIENT")
        self.connect_to_queue_and_check_messages()
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTRCLIENT",
            "version": "1.01",
            "parent": [ "gg6:aa6:vv6:pp6" ],
            "client": "TEST_CLIENT",
            "path": "gg:aa:vv:pp",
            "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTRCLIENT", "version": "1.01", "client": "TEST_CLIENT", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})

    @mock.patch('requests.post')
    def test_rpc_register_add_checksum__customer_not_set(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"), citype="TESTDSTRCLIENT", version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        rqmock.assert_not_called()

    @mock.patch('requests.post')
    def test_rpc_register_add_checksum__not_enough_data(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "add_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"), citype=None)
        self.connect_to_queue_and_check_messages()
        rqmock.assert_not_called()

    # the same but update succoess
    @mock.patch('requests.post')
    def test_rpc_register_update_checksum__standard(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "update_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, 
                checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"), citype="TESTDSTR", version="1.01", parent=["gg6:aa6:vv6:pp6"])
        self.connect_to_queue_and_check_messages()
        rqmock.assert_called_once_with("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})
    
    @mock.patch('requests.post')
    def test_rpc_register_update_checksum__customer(self, rqmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "update_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(201, kwargs.get("json"))

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, 
                checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"), citype="TESTDSTRCLIENT", version="1.01", parent=["gg6:aa6:vv6:pp6"], client="TEST_CLIENT")
        self.connect_to_queue_and_check_messages()
        rqmock.assert_called_once_with("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTRCLIENT", "version": "1.01", "client": "TEST_CLIENT", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})

    # registration fail
    @mock.patch('requests.post')
    def test_rpc_register_checksum_fail(self, rqmock):
        def _retval(*args, **kwargs):
            return MockResponse(409, "Conflict")

        rqmock.side_effect = _retval

        location = ("gg:aa:vv:pp", "NXS", 1)
        self.rpc.register_checksum(location, 
                checksum=NexusAPIMock().info("gg:aa:vv:pp").get("md5"), citype="TESTDSTR", version="1.01", parent=["gg6:aa6:vv6:pp6"])

        self.connect_to_queue_and_check_messages(1, 0, 1)
        self.assertEqual(rqmock.call_count, 2)
        rqmock.assert_any_call("http://distro-api-test/add_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "parent": [ "gg6:aa6:vv6:pp6" ], "client": "", "path": "gg:aa:vv:pp",
            "checksum": NexusAPIMock().info("gg:aa:vv:pp").get("md5")})
        rqmock.assert_any_call("http://distro-api-test/update_distributive", json={
            "citype": "TESTDSTR", "version": "1.01", "client": "", "changes": {
                "parent": [ "gg6:aa6:vv6:pp6" ],
                "path": "gg:aa:vv:pp",
                "checksum":  NexusAPIMock().info("gg:aa:vv:pp").get("md5")}})



    # delete nonexistent artifact
    @mock.patch('requests.post')
    @mock.patch('requests.delete')
    def test_delete_nonexistent_file(self, delmock, postmock):
        def _retval(*args, **kwargs):
            if posixpath.basename(args[0]) != "delete_distributive":
                return MockResponse(404, "Not Found")

            return MockResponse(200, kwargs.get("json"))

        delmock.side_effect = _retval
        postmock.side_effect = _retval
        location=("this.trash.surely.does.not.exist.in:nexus:x.x.x:pkg", "NXS", 0)
        self.assertFalse(NexusAPIMock().exists(location[0]))

        # by gav
        self.rpc.register_file(location, citype="TESTDSTRCLIENT", remove=True, version="1.01", client="TEST_CLIENT")
        # by checksum
        _tempfile = TemporaryFile()
        _tempfile.write(str(location).encode('utf8'))
        _tempfile.seek(0,0)
        self.rpc.register_checksum(location, checksum=self._md5(_tempfile), version="1.01", client="TEST_CLIENT")
        _tempfile.close()
        self.connect_to_queue_and_check_messages(2, 2, 0)
        # only once should be calledonly once should be called since 'remove' property is not set by default and we are unable to change it in 'register_checksum'
        self.assertEqual(delmock.call_count, 1)
        postmock.assert_not_called()


    # delete nonexistent artifact
    @mock.patch('requests.post')
    @mock.patch('requests.delete')
    def test_rpc_skipping_file_registration_for_non_nexus_paths__standard(self, delmock, postmock):
        svn_location = ["https://vcs-svn.example.com/some_script.sql", "SVN", 1]
        smb_location = ["smb://fstest.example.com/YO/example_release_notes.txt", "SMB", 1] 
        self.rpc.register_file(svn_location, "TESTDSTR", remove=True, version="1.01")
        self.rpc.register_file(smb_location, "TESTDSTR", remove=True, version="1.01")
        self.connect_to_queue_and_check_messages(msg_count=2, good_msg_count=2)
        delmock.assert_not_called()
        postmock.assert_not_called()
    
    @mock.patch('requests.post')
    @mock.patch('requests.delete')
    def test_rpc_skipping_checksum_registration_for_non_nexus_paths__client(self, delmock, postmock):
        svn_location = ["https://vcs-svn.example.com/some_script.sql", "SVN", 1]
        smb_location = ["smb://fstest.example.com/YO/example_release_notes.txt", "SMB", 1] 
        self.rpc.register_checksum(svn_location, "f8b723fdfa213027407c6d652433d794", "TESTDSTR")
        self.rpc.register_checksum(smb_location, "f8b723fdfa213027407c6d652433d795", "TESTDSTR")
        self.connect_to_queue_and_check_messages(msg_count=2, good_msg_count=2)
        delmock.assert_not_called()
        postmock.assert_not_called()
