"""Private work-only storage. Never expose this directory through a static route."""
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from flask import current_app


class PrivateStorage:
    def path(self, key):
        root = Path(current_app.config['WORK_FILE_ROOT']).resolve()
        candidate = (root / key).resolve()
        if not key.startswith('work/files/') or root not in candidate.parents:
            raise ValueError('Invalid private object key')
        return candidate

    def put_object(self, key, stream, length=None, content_type=None):
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=target.parent)
        total = 0
        try:
            with os.fdopen(fd, 'wb') as output:
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    if total > current_app.config.get('WORK_FILE_MAX_MB', 25) * 1024 * 1024:
                        raise ValueError('File exceeds configured maximum')
                    output.write(chunk)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def stat_object(self, key):
        return SimpleNamespace(size=self.path(key).stat().st_size)

    def get_object(self, key, offset=None, length=None):
        import io
        if offset is not None or length is not None:
            with self.path(key).open('rb') as stream:
                stream.seek(offset or 0)
                return io.BytesIO(stream.read(length))
        return self.path(key).open('rb')

    def remove_object(self, key):
        self.path(key).unlink(missing_ok=True)


storage = PrivateStorage()
