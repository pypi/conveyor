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

import asyncio
import os
import threading

import aiohttp
import aiohttp.web
from aiohttp.web_middlewares import normalize_path_middleware
from aiobotocore.session import get_session as aiobotocore_get_session

from .views import not_found, redirect, health, documentation, documentation_top, index
from .tasks import redirects_refresh_task


async def session_close(app):
    http_session = app.get("http.session")
    if http_session is not None:
        await http_session.close()
    app.get("boto.session")().close()

async def cancel_tasks(app):
    for task in app["tasks"]:
        await task.cancel()


def configure():
    app = aiohttp.web.Application()

    # Pull configuration out of the environment
    app["settings"] = {
        "endpoint": os.environ["CONVEYOR_ENDPOINT"],
        "docs_bucket": os.environ["DOCS_BUCKET"],
    }

    # Setup a HTTP session for our clients to share connections with and
    # register a shutdown callback to close the session.
    app["http.session"] = aiohttp.ClientSession(
        loop=asyncio.get_event_loop(),
        headers={"User-Agent": "conveyor"},
    )

    # https://github.com/boto/botocore/issues/2047#issuecomment-1251318969
    _aio_session_cache = threading.local()
    def _cached_aiobotocore_session():
        if not hasattr(_aio_session_cache, "session"):
            _aio_session_cache.session = aiobotocore_get_session()
        return _aio_session_cache.session
    app["boto.session"] = _cached_aiobotocore_session

    app.on_shutdown.append(session_close)

    app["tasks"] = []

    app["redirects"] = {}
    _fetch_redirects_task = asyncio.ensure_future(
        redirects_refresh_task(app),
        loop=asyncio.get_event_loop(),
    )

    app.on_shutdown.append(cancel_tasks)

    # Add routes and views to our application
    app.router.add_route(
        "GET",
        "/packages/{python_version}/{project_l}/{project_name}/{filename}",
        redirect,
    )
    app.router.add_route(
        "HEAD",
        "/packages/{python_version}/{project_l}/{project_name}/{filename}",
        redirect,
    )
    app.router.add_route(
        "GET",
        "/packages/{tail:.*}",
        not_found,
    )
    app.router.add_route(
        "GET",
        "/packages",
        not_found,
    )

    app.router.add_route(
        "GET",
        "/_health/",
        health,
    )
    app.router.add_route(
        "GET",
        "/_health",
        health,
    )

    # Add Documentation routes
    app.router.add_route(
        "GET",
        "/",
        index,
    )
    app.router.add_route(
        "HEAD",
        "/",
        index,
    )
    app.router.add_route(
        "GET",
        "/{project_name}/{path:.*}",
        documentation,
    )
    app.router.add_route(
        "GET",
        "/{project_name}",
        documentation_top,
    )

    return app
