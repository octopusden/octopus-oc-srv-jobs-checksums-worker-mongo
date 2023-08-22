from ..checksums_worker_mongo import QueueWorkerApplicationMongo
from oc_cdt_queue2.test.synchron.mocks.queue_application import QueueApplication
from oc_cdtapi.NexusAPI import NexusAPIError

class NexusAPIMock():
    def __init__(self):
        self.afacts = {
                "gg:aa:vv:pp": {"md5": "ecfef802f0e970ae8865e76ace6f5f8e", "mime": "x-file/hell"},
                "gg1:aa1:vv1:pp1": {"md5": "b73bbeff358443d86a3e39c6da278bb5", "mime": "x-file/lazhaa"},
                "this.is.trash:bullshit:x.x.x:pkg": {
                    "md5": "f8b723fdfa213027407c6d652433d794", "mime": "x-file/bullshit"},
                "this.is.trash.without.md5:bullshit:x.x.x:pkg": {}
                }
    def exists(self, path):
        return path in self.afacts.keys()

    def info(self, path):
        return self.afacts.get(path)

    def cat(self, gav, repo=None, binary=False, response=False, stream=False, encoding=None, enc_errors=None,
            write_to=None, rest_call=False, **argv):

        if not self.exists(gav):
            raise NexusAPIError(code=404, url=path, text=f"{path} not found")

        if write_to:
            write_to.write(gav.encode('utf8'))
            return

        return gav.encode('utf8')

class MockResponse:
    def __init__(self, status_code, json_data):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json_data

    def json(self):
        return json.loads(self.json_data)

class QueueWorkerApplicationMock(QueueWorkerApplicationMongo, QueueApplication):
    connect = QueueApplication.connect
    run = QueueApplication.run
    main = QueueApplication.main
    _connect_and_run = QueueApplication._connect_and_run

