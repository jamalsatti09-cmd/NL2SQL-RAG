import pytest
from unittest.mock import patch, MagicMock
import numpy as np

@pytest.fixture(autouse=True)
def mock_sentence_transformer():
    """
    Globally mocks the SentenceTransformer class to avoid network downloads
    and PyTorch initialization crashes on Windows under Python 3.14.
    """
    mock_model = MagicMock()
    # Mock SentenceTransformer's encode method to return fixed-dimension arrays
    mock_model.encode.side_effect = lambda texts, **kwargs: np.array([[0.1] * 384 for _ in texts])

    with patch("nl2sql_rag.vector_store.embedder.SentenceTransformer", return_value=mock_model) as mock_class:
        yield mock_model
