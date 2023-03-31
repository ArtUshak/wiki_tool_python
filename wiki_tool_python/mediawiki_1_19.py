"""MediaWiki API 1.31."""
import datetime
from typing import BinaryIO, Dict, Iterator, List, Optional

import requests

from mediawiki import (CanNotDelete, MediaWikiAPI, MediaWikiAPIMiscError,
                       PageProtected, StatusCodeError)
from requests_wrapper import ThrottledSession


class MediaWikiAPI1_19(MediaWikiAPI):
    """MediaWiki API 1.19 class with authentication data."""

    api_url: str
    index_url: str
    session: requests.Session
    edit_tokens: Dict[str, str]
    delete_tokens: Dict[str, str]

    def __init__(self, url: str, request_interval: float, user_agent: str):
        """Create MediaWiki API 1.19 class with given API URL."""
        self.api_url = f'{url}/api.php'
        self.index_url = f'{url}/index.php'
        self.session = ThrottledSession(request_interval)
        self.session.headers.update({
            'user-agent': user_agent
        })
        self.edit_tokens = {}
        self.delete_tokens = {}

    def get_namespace_list(self) -> List[int]:
        """Iterate over namespaces in wiki."""
        params: Dict[str, object] = {
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
                map(
                    int,
                    namespaces.keys()
                )
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
        params: Dict[str, object] = {
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

        r = self.session.get(self.api_url, params=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            raise MediaWikiAPIMiscError(data['error'])

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

    def get_category_members(
        self, category_name: str, limit: int,
        namespace: Optional[int] = None, member_type: Optional[str] = None
    ) -> Iterator[Dict[str, object]]:
        """Iterate over pages in category `category_name`."""
        raise NotImplementedError()

    def get_image_list(self, limit: int) -> Iterator[Dict[str, str]]:
        """
        Iterate over all images in wiki.

        Each image data is dictionary with two fields: `title` and `url`.
        """
        params: Dict[str, object] = {
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

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['allimages']

    def get_page_image_list(
        self, image_ids_limit: int, page_ids: List[int]
    ) -> Iterator[Dict[str, str]]:
        """Iterate over images with given page IDs."""
        raise NotImplementedError()

    def get_page_list(
        self, namespace: int, limit: int, first_page: Optional[str] = None,
        redirect_filter_mode: str = 'all'
    ) -> Iterator[str]:
        """Iterate over all page names in wiki in `namespace`."""
        params: Dict[str, object] = {
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

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['allpages']

    def get_page(
        self, title: str,
    ) -> str:
        """Get text of page with `title`."""
        params: Dict[str, object] = {
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
        """Search pages in wiki in `namespace` with `search_request`."""
        raise NotImplementedError()

    def get_deletedrevs_list(
        self, namespace: int, limit: int
    ) -> Iterator[Dict[str, object]]:
        """Iterate over deleted revisions in wiki in `namespace`."""
        params: Dict[str, object] = {
            'action': 'query',
            'list': 'deletedrevs',
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

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['deletedrevs']

    def delete_page(
            self, page_name: str, reason: Optional[str] = None
    ) -> None:
        """Delete page."""
        params: Dict[str, object] = {
            'action': 'delete',
            'title': page_name,
            'format': 'json',
        }
        if reason is not None:
            params['reason'] = reason
        if page_name not in self.delete_tokens:
            self.delete_tokens.update(self.get_tokens('delete', page_name))
        params['token'] = self.delete_tokens[page_name]

        self.call_api(params)

    def edit_page(
            self, page_name: str, text: str, summary: Optional[str] = None
    ) -> None:
        """Delete page."""
        params: Dict[str, object] = {
            'action': 'edit',
            'title': page_name,
            'text': text,
            'format': 'json',
        }
        if summary is not None:
            params['summary'] = summary
        if page_name not in self.edit_tokens:
            self.edit_tokens.update(self.get_tokens('edit', page_name))
        params['token'] = self.edit_tokens[page_name]

        self.call_api(params)

    def upload_file(
        self, file_name: str, file: BinaryIO, mime_type: Optional[str],
        text: Optional[str] = None, ignore_warnings: bool = True
    ) -> None:
        """Upload file."""
        raise NotImplementedError()

    def get_tokens(self, token_type: str, titles: str) -> Dict[str, str]:
        """Return page tokens for API."""
        params: Dict[str, object] = {
            'action': 'query',
            'prop': 'info',
            'titles': titles,
            'intoken': token_type,
            'format': 'json',
        }

        data = self.call_api(params)

        return dict(map(
            lambda page_data:
                (
                    page_data['title'], page_data['f{token_type}token']
                ),
            data['query']['pages'].values()
        ))

    def get_backlinks(
        self, title: str, namespace: Optional[int], limit: int
    ) -> Iterator[Dict[str, object]]:
        """Get list of pages which has links to given page."""
        params: Dict[str, object] = {
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

            data = self.call_api(current_params)

            backlinks = data['query']['backlinks']

            for backlink in backlinks:
                yield backlink

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['backlinks']

    def api_login(self, username: str, password: str) -> None:
        """Log in to MediaWiki API."""
        params1: Dict[str, object] = {
            'action': 'login',
            'format': 'json',
            'lgname': username,
            'lgpassword': password,
        }

        data1 = self.call_api(params1, is_post=True)

        if data1['login']['result'] == 'Success':
            return

        if data1['login']['result'] != 'NeedToken':
            raise MediaWikiAPIMiscError('Login result is {}'.format(
                data1['login']['result']
            ))

        params2: Dict[str, object] = {
            'action': 'login',
            'format': 'json',
            'lgname': username,
            'lgpassword': password,
            'lgtoken': data1['login']['token'],
        }

        data2 = self.call_api(params2, is_post=True)

        if data2['login']['result'] != 'Success':
            raise MediaWikiAPIMiscError('Login result is {}'.format(
                data2['login']['result']
            ))

    def call_api(
        self, params: Dict[str, object], is_post: bool = False
    ) -> Dict[str, object]:
        """
        Perform request to MediaWiki API.

        Get token if necessary, raise exception on error.
        """
        if is_post:
            r = self.session.post(self.api_url, data=params)
        else:
            r = self.session.get(self.api_url, params=params)

        if r.status_code != 200:
            raise StatusCodeError(f'Status code is {r.status_code}')

        data = r.json()
        if 'error' in data:
            if 'code' in data['error']:
                if data['error']['code'] == 'cantdelete':
                    raise CanNotDelete(data['error']['info'])
                if data['error']['code'] == 'protectedpage':
                    raise PageProtected(data['error'])
            raise MediaWikiAPIMiscError(data['error'])
        if 'warning' in data:
            raise MediaWikiAPIMiscError(data['warning'])

        return data
