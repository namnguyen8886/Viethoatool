import asyncio
import re
from typing import Tuple
import aiohttp
from cau_hinh.cai_dat import cai_dat_he_thong
from dieu_phoi.ghi_log import log
from loi.backoff import tinh_backoff
from datetime import datetime

SUPPORTED_LANGUAGES = {
    'auto': 'Auto Detect',
    'en': 'English', 'vi': 'Vietnamese', 'ja': 'Japanese',
    'ko': 'Korean', 'zh-CN': 'Chinese Simplified', 'zh-TW': 'Chinese Traditional',
    'fr': 'French', 'de': 'German', 'es': 'Spanish',
    'ru': 'Russian', 'th': 'Thai', 'id': 'Indonesian',
    'pt': 'Portuguese', 'ar': 'Arabic',
}

class bo_nhan_dien_ngon_ngu:
    @staticmethod
    def lay_ten_ngon_ngu(code: str) -> str:
        return SUPPORTED_LANGUAGES.get(code, code)
    @staticmethod
    def lay_tat_ca() -> dict:
        return SUPPORTED_LANGUAGES.copy()

class gemini_loi:
    def __init__(self, cai_dat: cai_dat_he_thong):
        self.cai_dat = cai_dat
        self.keys = [k.strip() for k in cai_dat.gemini_api_keys if k and k.strip() and not k.startswith('YOUR_')]
        self.models = list(cai_dat.gemini_models)
        self.key_index = 0
        self.model_index = 0
        self.statistics = {'requests': 0, 'successful': 0, 'failed': 0, 'cache_hits': 0}
        self.failed_keys: set = set()
        self.key_status: dict = {}
        self.current_model: str | None = None
        self.backoff = tinh_backoff(base=cai_dat.exponential_backoff_base, max_time=cai_dat.max_backoff_time)

    def them_key(self, key: str):
        key = key.strip()
        if key and key not in self.keys:
            self.keys.append(key)

    def _get_key(self) -> str:
        if not self.keys:
            raise ValueError('Chua co API key! Them key vao .env hoac qua panel')
        for _ in range(len(self.keys)):
            key = self.keys[self.key_index % len(self.keys)]
            self.key_index += 1
            if key not in self.failed_keys:
                return key
        self.failed_keys.clear()
        key = self.keys[self.key_index % len(self.keys)]
        self.key_index += 1
        return key

    def _mark_key_failed(self, key: str, reason: str = 'unknown'):
        self.failed_keys.add(key)
        self.key_status[key] = {'status': 'failed', 'reason': reason,
                                'time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

    def _get_model(self) -> str:
        model = self.models[self.model_index % len(self.models)]
        self.current_model = model
        return model

    def get_current_model(self) -> str:
        return self.current_model or self._get_model()

    def _create_prompt(self, content: str, filename: str, lang_from='auto', lang_to='vi', file_type='text') -> str:
        lf = bo_nhan_dien_ngon_ngu.lay_ten_ngon_ngu(lang_from)
        lt = bo_nhan_dien_ngon_ngu.lay_ten_ngon_ngu(lang_to)
        return f"""Translate from {lf} to {lt}.

RULES (MUST FOLLOW):
1. Return ONLY translated content. NO explanations, NO notes, NO footers, NO metadata
2. PRESERVE file structure ({file_type} format) exactly
3. PRESERVE placeholders: %player%, {{{{player}}}}, <player>, {{{{0}}}}
4. PRESERVE color/style codes: &a &b §a §b &#RRGGBB <red> <bold> <italic>
5. PRESERVE line breaks: \\n <br> \\t
6. PRESERVE config keys - translate values only
7. DO NOT translate: URLs, paths, /commands, permission.nodes, numbers, booleans
8. DO NOT add any comment/footer/watermark to output

FILE: {filename} | TYPE: {file_type}

CONTENT:
{content}"""

    async def translate_text(self, content: str, filename: str, lang_from='auto', lang_to='vi', file_type='text') -> Tuple[str, bool]:
        if not self.keys:
            log.warning('Khong co key Gemini')
            return content, False
        prompt = self._create_prompt(content, filename, lang_from, lang_to, file_type)
        for attempt in range(self.cai_dat.max_retries):
            api_key = None
            try:
                api_key = self._get_key()
                model = self._get_model()
                url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
                payload = {
                    'contents': [{'parts': [{'text': prompt}]}],
                    'generationConfig': {'temperature': 0.1, 'topP': 0.95, 'maxOutputTokens': 65536},
                    'safetySettings': [
                        {'category': f'HARM_CATEGORY_{c}', 'threshold': 'BLOCK_NONE'}
                        for c in ['HARASSMENT', 'HATE_SPEECH', 'SEXUALLY_EXPLICIT', 'DANGEROUS_CONTENT']
                    ]
                }
                timeout = aiohttp.ClientTimeout(total=self.cai_dat.api_timeout)
                self.statistics['requests'] += 1
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, params={'key': api_key}, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if 'candidates' in data and data['candidates']:
                                parts = data['candidates'][0].get('content', {}).get('parts', [])
                                if parts and 'text' in parts[0]:
                                    # [FIX] KHONG chen footer - pha vo YAML/JSON/config
                                    result = parts[0]['text'].strip()
                                    result = re.sub(r'^```[\w]*\n?', '', result)
                                    result = re.sub(r'\n?```$', '', result)
                                    self.statistics['successful'] += 1
                                    self.key_status[api_key] = {'status': 'working', 'model': model}
                                    log.info(f'OK [{model}] {filename}')
                                    return result.strip(), True
                        elif resp.status == 429:
                            self._mark_key_failed(api_key, 'rate_limit')
                            await asyncio.sleep(self.backoff.tinh(attempt))
                            continue
                        elif resp.status == 400:
                            err = await resp.text()
                            if 'API key not valid' in err:
                                self._mark_key_failed(api_key, 'invalid')
                                continue
                        elif resp.status in (503, 500):
                            self.model_index += 1
                            await asyncio.sleep(self.backoff.tinh(attempt))
                            continue
                await asyncio.sleep(self.cai_dat.delay_giua_request)
            except asyncio.TimeoutError:
                if api_key: self._mark_key_failed(api_key, 'timeout')
                self.model_index += 1
                await asyncio.sleep(self.backoff.tinh(attempt))
            except Exception as e:
                log.warning(f'Loi: {e}')
                await asyncio.sleep(self.backoff.tinh(attempt))
        self.statistics['failed'] += 1
        return content, False

    def thong_ke(self) -> dict:
        return {
            'statistics': self.statistics.copy(),
            'models': self.models, 'current_model': self.current_model,
            'total_keys': len(self.keys), 'failed_keys': len(self.failed_keys),
            'key_status': self.key_status.copy(),
        }
