"""MediaWiki API 1.31."""
import datetime
from typing import BinaryIO, Dict, Iterator, List, Optional, Union

import requests
import requests_toolbelt

from mediawiki import (CanNotDelete, MediaWikiAPI, MediaWikiAPIMiscError,
                       PageProtected, StatusCodeError)
from requests_wrapper import ThrottledSession

ParamsDict = Dict[str, Union[None, str, int]]


class MediaWikiAPI1_31(MediaWikiAPI):
    """MediaWiki API 1.31 class with authentication data."""

    api_url: str
    index_url: str
    session: requests.Session
    csrf_token: Optional[str]

    def __init__(self, url: str, request_interval: float, user_agent: str):
        """Create MediaWiki API 1.31 class with given API URL."""
        self.api_url = f'{url}/api.php'
        self.index_url = f'{url}/index.php'
        self.session = ThrottledSession(request_interval)
        self.session.headers.update({
            'user-agent': user_agent
        })
        self.csrf_token = None

    def get_namespace_list(self) -> List[int]:
        """Iterate over namespaces in wiki."""
        params: ParamsDict = {
            'action': 'query',
            'meta': 'siteinfo',
            'siprop': 'namespaces',
            'format': 'json',
        }

        data = self.call_api(params)
        namespaces = data['query']['namespaces']

        return list(
            filter(
                lambda namespace_id: namespace_id >= 0,
                map(int, namespaces.keys())
            )
        )

    def get_user_contributions_list(
        self, namespace: int, limit: int, user: str,
        start_date: datetime.datetime, end_date: datetime.datetime,
    ) -> Iterator[Dict[str, object]]:
        """
        Iterate over user edits.

        Iterate over all edits made by `user in `namespace` since `start_date`
        until `end_date`.
        """
        params: ParamsDict = {
            'action': 'query',
            'list': 'usercontribs',
            'uclimit': limit,
            'ucnamespace': namespace,
            'ucuser': user.replace(' ', '_'),
            'ucdir': 'newer',
            'format': 'json',
        }
        if start_date is not None:
            params['ucstart'] = int(start_date.timestamp())
        if end_date is not None:
            params['ucend'] = int(end_date.timestamp())
        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)

            data = self.call_api(current_params)
            user_contribs = data['query']['usercontribs']

            for user_contrib in user_contribs:
                yield user_contrib

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['usercontribs']

    def get_image_list(self, limit: int) -> Iterator[Dict[str, str]]:
        """
        Iterate over all images in wiki.

        Each image data is dictionary with two fields: `title` and `url`.
        """
        params: ParamsDict = {
            'action': 'query',
            'list': 'allimages',
            'aidir': 'ascending',
            'ailimit': limit,
            'format': 'json',
        }
        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)

            data = self.call_api(current_params)
            images = data['query']['allimages']

            for image_data in images:
                yield {
                    'title': image_data['title'],
                    'url': image_data['url'],
                }

            if 'continue' not in data:
                break
            last_continue = data['continue']

    def get_page_image_list(
        self, image_ids_limit: int, page_ids: List[int]
    ) -> Iterator[Dict[str, str]]:
        """Iterate over images with given page IDs."""
        params: ParamsDict = {
            'action': 'query',
            'prop': 'imageinfo',
            'iiprop': 'url',
            'iilimit': 1,
            'format': 'json',
        }

        i: int = 0
        while i < len(page_ids):
            current_params = params.copy()
            page_ids_group: List[int]
            if (i + image_ids_limit) >= len(page_ids):
                page_ids_group = page_ids[i:]
            else:
                page_ids_group = page_ids[i:i + image_ids_limit]
            current_params['pageids'] = '|'.join(
                list(map(str, page_ids_group))
            )

            data = self.call_api(current_params)
            pages_data = data['query']['pages']

            for page_id in pages_data:
                page_data = pages_data[page_id]
                yield {
                    'title': page_data['title'],
                    'url': page_data['imageinfo'][0]['url'],
                }

            i += image_ids_limit

    def get_category_members(
        self, category_name: str, limit: int,
        namespace: Optional[int] = None, member_type: Optional[str] = None
    ) -> Iterator[Dict[str, object]]:
        """
        Iterate over pages in category `category_name`.

        `member_type` can be `None`, `page`, 'subcat` or `file`.
        """
        params: ParamsDict = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': category_name,
            'cmdir': 'ascending',
            'cmlimit': limit,
            'format': 'json',
        }
        if member_type in ['page', 'subcat', 'file']:
            params['cmtype'] = member_type
        if namespace is not None:
            params['cmnamespace'] = namespace
        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)

            data = self.call_api(current_params)
            pages = data['query']['categorymembers']

            for page_data in pages:
                yield page_data

            if 'continue' not in data:
                break
            last_continue = data['continue']

    def get_page_list(
        self, namespace: int, limit: int, first_page: Optional[str] = None,
        redirect_filter_mode: str = 'all'
    ) -> Iterator[str]:
        """Iterate over all page names in wiki in `namespace`."""
        params: ParamsDict = {
            'action': 'query',
            'list': 'allpages',
            'apnamespace': namespace,
            'apdir': 'ascending',
            'apfilterredir': redirect_filter_mode,
            'aplimit': limit,
            'format': 'json',
        }
        if first_page is not None:
            params['apfrom'] = first_page
        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)

            data = self.call_api(current_params)
            pages = data['query']['allpages']

            for page_data in pages:
                yield page_data['title']

            if 'continue' not in data:
                break
            last_continue = data['continue']

    def get_page(
        self, title: str
    ) -> str:
        """Get text of page with `title`."""
        params: ParamsDict = {
            'action': 'raw',
            'title': title,
        }

        r = self.session.get(self.index_url, params=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        return r.text

    def search_pages(
        self, search_request: str, namespace: int, limit: int,
    ) -> Iterator[str]:
        """Iterate over all page names in wiki in `namespace`."""
        params: ParamsDict = {
            'action': 'query',
            'list': 'search',
            'srnamespace': namespace,
            'srlimit': limit,
            'format': 'json',
            'srsearch': search_request,
            'srwhat': 'text',
        }
        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)

            data = self.call_api(params)
            pages = data['query']['search']

            for page_data in pages:
                yield page_data['title']

            if 'continue' not in data:
                break
            last_continue = data['continue']

    def get_deletedrevs_list(
        self, namespace: int, limit: int
    ) -> Iterator[Dict[str, object]]:
        """Iterate over deleted revisions in wiki in `namespace`."""
        params: ParamsDict = {
            'action': 'query',
            'list': 'deletedrevs',  # TODO: deprecated since MediaWiki 1.25
            'drnamespace': namespace,
            'drdir': 'newer',
            'drlimit': limit,
            'drprop': 'revid|user|comment|content',
            'format': 'json',
        }
        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)

            data = self.call_api(current_params)
            deletedrevs = data['query']['deletedrevs']

            for deletedrev_data in deletedrevs:
                title: str = deletedrev_data['title']

                for revision in deletedrev_data['revisions']:
                    revision.update({'title': title})
                    yield revision

            if 'continue' not in data:
                break
            last_continue = data['continue']

    def delete_page(
            self, page_name: str, reason: Optional[str] = None
    ) -> None:
        """Delete page."""
        params: ParamsDict = {
            'action': 'delete',
            'title': page_name,
            'format': 'json',
        }
        if reason is not None:
            params['reason'] = reason

        self.call_api(params, is_post=True, need_token=True)

    def edit_page(
            self, page_name: str, text: str, summary: Optional[str] = None
    ) -> None:
        """Edit page, setting new text."""
        params: ParamsDict = {
            'action': 'edit',
            'title': page_name,
            'text': text,
            'format': 'json',
            'bot': True
        }
        if summary is not None:
            params['summary'] = summary

        self.call_api(params, is_post=True, need_token=True)

    def upload_file(
        self, file_name: str, file: BinaryIO, mime_type: Optional[str],
        text: Optional[str] = None, ignore_warnings: bool = True
    ) -> None:
        """Upload file."""
        if self.csrf_token is None:
            self.csrf_token = self.get_token('csrf')

        params: ParamsDict = {
            'action': 'upload',
            'filename': file_name,
            'token': self.csrf_token,
            'format': 'json',
            'async': '1',  # TODO
            'file': (file_name, file, mime_type),
        }
        if ignore_warnings:
            params['ignorewarnings'] = '1'
        if text is not None:
            params['text'] = text

        encoder = requests_toolbelt.MultipartEncoder(fields=params)

        r = self.session.post(
            self.api_url, data=encoder,
            headers={
                'Content-Type': encoder.content_type,
            }
        )
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            raise MediaWikiAPIMiscError(data['error'])

    def get_token(self, token_type: str) -> str:
        """Return CSRF token for API."""
        params: ParamsDict = {
            'action': 'query',
            'meta': 'tokens',
            'type': token_type,
            'format': 'json',
        }

        data = self.call_api(params)

        return data['query']['tokens'][f'{token_type}token']

    def get_backlinks(
        self, title: str, namespace: Optional[int], limit: int
    ) -> Iterator[Dict[str, object]]:
        """Get list of pages which has links to given page."""
        params: ParamsDict = {
            'action': 'query',
            'list': 'backlinks',
            'bltitle': title,
            'bllimit': limit,
            'format': 'json',
        }
        if namespace is not None:
            params['blnamespace'] = namespace

        last_continue: Dict[str, object] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)
            r = self.session.get(self.api_url, params=current_params)
            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data = r.json()
            if 'error' in data:
                if data['error']['code'] == 'protectedpage':
                    raise PageProtected(data['error'])
                raise MediaWikiAPIMiscError(data['error'])
            backlinks = data['query']['backlinks']

            for backlink in backlinks:
                yield backlink

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['backlinks']

    def api_login(self, username: str, password: str) -> None:
        """Log in to MediaWiki API."""
        token = self.get_token('login')

        params: ParamsDict = {
            'action': 'login',
            'format': 'json',
            'lgname': username,
            'lgpassword': password,
            'lgtoken': token,
        }

        self.call_api(params, is_post=True, need_token=False)

    def call_api(
        self, params: Dict[str, object], is_post: bool = False,
        need_token: bool = False, token_retry: bool = True
    ) -> Dict[str, object]:
        """
        Perform request to MediaWiki API.

        Get token if necessary, raise exception on error.
        """
        while True:
            if need_token:
                if self.csrf_token is None:
                    self.csrf_token = self.get_token('csrf')
                params['token'] = self.csrf_token

            if is_post:
                r = self.session.post(self.api_url, data=params)
            else:
                r = self.session.get(self.api_url, params=params)

            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data: Dict[str, object] = r.json()
            if 'error' in data:
                if need_token and token_retry:
                    if data['error']['code'] == 'badtoken':
                        self.csrf_token = self.get_token('csrf')
                        continue
                if 'code' in data['error']:
                    if data['error']['code'] == 'cantdelete':
                        raise CanNotDelete(data['error']['info'])
                    if data['error']['code'] == 'protectedpage':
                        raise PageProtected(data['error'])
                raise MediaWikiAPIMiscError(data['error']['info'])

            return data
