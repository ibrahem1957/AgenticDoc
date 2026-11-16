from __future__ import annotations

import time

time.sleep(1)

from tests.lab.stub_adapters import StubAdapter  # noqa: E402


ADAPTER_VERSION = "1"


def create_adapter(info):
    return StubAdapter(info)
