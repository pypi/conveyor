# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pretend
import pytest

from conveyor.config import session_close, configure


@pytest.mark.asyncio
async def test_session_close():
    @pretend.call_recorder
    async def close():
        pass

    app = {
        "http.session": pretend.stub(close=close),
        "boto.session": lambda: pretend.stub(close=close),
    }

    await session_close(app)

    assert close.calls == [pretend.call(), pretend.call()]
