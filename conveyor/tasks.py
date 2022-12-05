
import asyncio
import concurrent.futures
import json

import botocore

from botocore.config import Config as BotoCoreConfig

ANON_CONFIG = BotoCoreConfig(signature_version=botocore.UNSIGNED)


async def fetch_key(s3, bucket, key):
    resp = await s3.get_object(
        Bucket=bucket,
        Key=key,
    )
    return resp


async def redirects_refresh_task(app):
    while True:
        try:
            try:
                bucket = app["settings"]["docs_bucket"]
                session = app["boto.session"]()
                etag = app["redirects"].get('_ETag')
                async with session.create_client('s3', config=ANON_CONFIG) as s3:
                    try:
                        key = await fetch_key(s3, bucket, 'redirects.txt')
                    except botocore.exceptions.ClientError:
                        await asyncio.sleep(60)
                        continue
                if etag != key['ETag']:
                    redirects = await key['Body'].read()
                    redirect_config = {
                        item['project_name']: {
                            'include_path': item['include_path'],
                            'base_uri': item['base_uri'],
                        }
                        for item in [json.loads(x) for x in redirects.split(b'\n') if x]
                    }
                    redirect_config['_ETag'] = key['ETag']
                    app["redirects"] = redirect_config
            except concurrent.futures.CancelledError:
                raise
            except Exception as exc:
                pass
            await asyncio.sleep(600)
        except concurrent.futures.CancelledError:
            return
