"""Unit tests: cross-encoder (NoOp, protocol)."""

import pytest

from sentiment_api.retrieval.cross_encoder import CrossEncoder, NoOpCrossEncoder, get_cross_encoder


def test_noop_returns_zero():
    enc = NoOpCrossEncoder()
    assert enc.score("query", "doc text") == 0.0


def test_get_cross_encoder_noop():
    enc = get_cross_encoder(use_noop=True)
    assert isinstance(enc, NoOpCrossEncoder)
    assert enc.score("q", "d") == 0.0


def test_cross_encoder_protocol():
    enc = NoOpCrossEncoder()
    assert isinstance(enc, CrossEncoder)
