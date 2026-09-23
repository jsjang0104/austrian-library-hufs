"""Real local indexes with mocked HF inference for database tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from library import search_service


class IsolatedSearchIndexMixin:
    def setUp(self):
        super().setUp()
        index_dir = TemporaryDirectory()
        self.addCleanup(index_dir.cleanup)
        for name, value in (
            ('INDEX_DIR', index_dir.name),
            ('INDEX_PATH', str(Path(index_dir.name) / 'books.faiss')),
        ):
            patcher = patch.object(search_service, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        search_service.reset_index()
        self.addCleanup(search_service.reset_index)
        hf = patch('huggingface_hub.InferenceClient.feature_extraction', autospec=True)
        self.hf = hf.start()
        self.addCleanup(hf.stop)
        self.hf.side_effect = lambda client, texts, **kwargs: np.ones((len(texts), 1024), dtype='float32')
