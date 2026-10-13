"""Only the training domain can decide visibility of training-owned objects."""
from flask import current_app, request
from workbench.auth import current_actor
from workbench.errors import unavailable
from workbench.collab.services.projections import WorkProjectionProvider, register_projection
import requests


class RemoteProjection(WorkProjectionProvider):
    def __init__(self, source_type, label, stewardable):
        self.source_type, self.label, self.stewardable = source_type, label, stewardable

    def fetch(self, source_id):
        actor = current_actor()
        cache = getattr(request, '_workbench_projections', {})
        key = (self.source_type, source_id)
        if key in cache:
            return cache[key]
        cfg = current_app.config
        url = cfg['IDENTITY_STATUS_URL'].rsplit('/', 1)[0] + '/projection'
        try:
            result = requests.post(url, json={'audience': cfg['IDENTITY_CLIENT_ID'],
                'subject': actor['account'].subject, 'source_type': self.source_type, 'source_id': source_id},
                auth=(cfg['IDENTITY_CLIENT_ID'], cfg['IDENTITY_CLIENT_SECRET']), timeout=(3, 5), allow_redirects=False)
            if result.status_code != 200 or len(result.content) > 16384:
                raise unavailable()
            data = result.json()
            if not isinstance(data, dict) or type(data.get('exists')) is not bool:
                raise unavailable()
        except (requests.RequestException, ValueError):
            raise unavailable() from None
        cache[key] = data
        request._workbench_projections = cache
        return data

    def exists(self, source_id):
        return self.fetch(source_id)['exists']

    def summarize(self, user, source_id):
        return self.fetch(source_id).get('projection')


for kind, label, stewardable in [('course', '课程', True), ('camp_session', '营期', False), ('feedback_ticket', '工单', False)]:
    register_projection(RemoteProjection(kind, label, stewardable))
