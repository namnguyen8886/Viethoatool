from __future__ import annotations

import os
from pathlib import Path

import aiohttp


class tai_len_gofile:
    def __init__(self):
        self.token = os.environ.get('GOFILE_TOKEN', '').strip()
        self.timeout = aiohttp.ClientTimeout(total=180)

    async def _lay_server(self, session: aiohttp.ClientSession) -> str:
        async with session.get('https://api.gofile.io/servers') as resp:
            data = await resp.json(content_type=None)
        servers = data.get('data', {}).get('servers', []) if isinstance(data, dict) else []
        if not servers:
            raise RuntimeError('Khong lay duoc server Gofile')
        server = servers[0]
        if isinstance(server, dict):
            return server.get('name') or server.get('server') or ''
        return str(server)

    async def tai_len(self, duong_dan: Path) -> dict:
        if not duong_dan.exists():
            raise FileNotFoundError(f'Khong tim thay file: {duong_dan}')
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        async with aiohttp.ClientSession(timeout=self.timeout, headers=headers) as session:
            server = await self._lay_server(session)
            if not server:
                raise RuntimeError('Khong xac dinh duoc server upload')
            url = f'https://{server}.gofile.io/contents/uploadfile'
            form = aiohttp.FormData()
            form.add_field('file', duong_dan.read_bytes(), filename=duong_dan.name, content_type='application/octet-stream')
            async with session.post(url, data=form) as resp:
                data = await resp.json(content_type=None)
            if data.get('status') != 'ok':
                raise RuntimeError(data.get('status', 'Upload Gofile that bai'))
            payload = data.get('data', {})
            link = payload.get('downloadPage') or payload.get('link') or payload.get('directLink')
            return {'ten_file': duong_dan.name, 'link': link or '', 'raw': payload}
