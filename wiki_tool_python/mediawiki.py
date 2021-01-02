"""MediaWiki API interaction functions."""
import datetime
from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Dict, Iterable, Iterator, List, Optional

import click
import requests
import requests_toolbelt

NAMESPACE_IMAGES = 6


class MediaWikiAPIError(click.ClickException):
    """MediaWiki API error."""


class StatusCodeError(MediaWikiAPIError):
    """Status code is not 200."""

    status_code: int

    def __init__(self, status_code: int):
        """Initialize."""
        self.status_code = status_code
        super().__init__(f'Status code is {status_code}')


class CanNotDelete(MediaWikiAPIError):
    """Page can not be deleted."""


class PageProtected(MediaWikiAPIError):
    """Page can not be edited because it is protected."""


class MediaWikiAPI(ABC):
    """Base MediaWiki API class."""

    @abstractmethod
    def get_namespace_list(self) -> Iterable[int]:
        """Get iterable of all namespaces in wiki."""
        raise NotImplementedError()

    @abstractmethod
    def get_user_contributions_list(
        self, namespace: int, limit: int, user: str,
        start_date: datetime.datetime, end_date: datetime.datetime,
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over user edits.

        Iterate over all edits made by `user in `namespace` since `start_date`
        until `end_date`.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_image_list(self, limit: int) -> Iterator[Dict[str, str]]:
        """
        Iterate over all images in wiki.

        Each image data is dictionary with two fields: `title` and `url`.
        """
        raise NotImplementedError()

    def get_page_image_list(
        self, image_ids_limit: int, page_ids: List[int]
    ) -> Iterator[Dict[str, str]]:
        """Iterate over images with given page IDs."""
        raise NotImplementedError()

    @abstractmethod
    def get_category_members(
        self, category_name: str, limit: int,
        namespace: Optional[int] = None, member_type: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over pages in category `category_name`."""
        raise NotImplementedError()

    @abstractmethod
    def get_page_list(
        self, namespace: int, limit: int, first_page: Optional[str] = None,
        redirect_filter_mode: str = 'all'
    ) -> Iterator[str]:
        """Iterate over all page names in wiki in `namespace`."""
        raise NotImplementedError()

    @abstractmethod
    def get_page(
        self, title: str,
    ) -> str:
        """Get text of page with `title`."""
        raise NotImplementedError()

    @abstractmethod
    def search_pages(
        self, search_request: str, namespace: int, limit: int,
    ) -> Iterator[str]:
        """Search pages in wiki in `namespace` with `search_request`."""
        raise NotImplementedError()

    @abstractmethod
    def get_deletedrevs_list(
        self, namespace: int, limit: int
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over deleted revisions in wiki in `namespace`."""
        raise NotImplementedError()

    @abstractmethod
    def upload_file(
        self, file_name: str, file: BinaryIO, mime_type: Optional[str],
        text: Optional[str] = None, ignore_warnings: bool = True
    ) -> None:
        """Upload file."""
        raise NotImplementedError()

    @abstractmethod
    def delete_page(
        self, page_name: str, reason: Optional[str] = None
    ) -> None:
        """Delete page."""
        raise NotImplementedError()

    @abstractmethod
    def edit_page(
        self, page_name: str, text: str, summary: Optional[str] = None
    ) -> None:
        """Edit page, setting new text."""
        raise NotImplementedError()

    @abstractmethod
    def get_backlinks(
        self, title: str, namespace: Optional[int], limit: int
    ) -> Iterator[Dict[str, Any]]:
        """Get list of pages which has links to given page."""
        raise NotImplementedError()

    @abstractmethod
    def api_login(self, username: str, password: str) -> None:
        """Log in to MediaWiki API."""
        raise NotImplementedError()


class MediaWikiAPI1_19(MediaWikiAPI):
    """MediaWiki API 1.19 class with authentication data."""

    api_url: str
    index_url: str
    session: requests.Session
    edit_tokens: Dict[str, str]
    delete_tokens: Dict[str, str]

    def __init__(self, url: str):
        """Create MediaWiki API 1.19 class with given API URL."""
        self.api_url = '{}/api.php'.format(url)
        self.index_url = '{}/index.php'.format(url)
        self.session = requests.Session()
        self.edit_tokens = {}
        self.delete_tokens = {}

    def get_namespace_list(self) -> List[int]:
        """Iterate over namespaces in wiki."""
        params: Dict[str, Any] = {
            'action': 'query',
            'meta': 'siteinfo',
            'siprop': 'namespaces',
            'format': 'json',
        }

        r = self.session.get(self.api_url, params=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            raise MediaWikiAPIError(data['error'])
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
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over user edits.

        Iterate over all edits made by `user in `namespace` since `start_date`
        until `end_date`.
        """
        params: Dict[str, Any] = {
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
        last_continue: Dict[str, Any] = {}

        r = self.session.get(self.api_url, params=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            raise MediaWikiAPIError(data['error'])

        while True:
            current_params = params.copy()
            current_params.update(last_continue)
            r = self.session.get(self.api_url, params=current_params)
            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data = r.json()
            if 'error' in data:
                raise MediaWikiAPIError(data['error'])
            user_contribs = data['query']['usercontribs']

            for user_contrib in user_contribs:
                yield user_contrib

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['usercontribs']

    def get_category_members(
        self, category_name: str, limit: int,
        namespace: Optional[int] = None, member_type: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over pages in category `category_name`."""
        raise NotImplementedError()

    def get_image_list(self, limit: int) -> Iterator[Dict[str, str]]:
        """
        Iterate over all images in wiki.

        Each image data is dictionary with two fields: `title` and `url`.
        """
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'allimages',
            'aidir': 'ascending',
            'ailimit': limit,
            'format': 'json',
        }
        last_continue: Dict[str, Any] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)
            r = self.session.get(self.api_url, params=current_params)
            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data = r.json()
            if 'error' in data:
                raise MediaWikiAPIError(data['error'])
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
        params: Dict[str, Any] = {
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
        last_continue: Dict[str, Any] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)
            r = self.session.get(self.api_url, params=current_params)
            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data = r.json()
            if 'error' in data:
                raise MediaWikiAPIError(data['error'])
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
        params: Dict[str, Any] = {
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
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over deleted revisions in wiki in `namespace`."""
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'deletedrevs',
            'drnamespace': namespace,
            'drdir': 'newer',
            'drlimit': limit,
            'drprop': 'revid|user|comment|content',
            'format': 'json',
        }
        last_continue: Dict[str, Any] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)
            r = self.session.get(self.api_url, params=current_params)
            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data = r.json()
            if 'error' in data:
                raise MediaWikiAPIError(data['error'])
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
        params: Dict[str, Any] = {
            'action': 'delete',
            'title': page_name,
            'format': 'json',
        }
        if reason is not None:
            params['reason'] = reason
        if page_name not in self.delete_tokens:
            self.delete_tokens.update(self.get_tokens('delete', page_name))
        params['token'] = self.delete_tokens[page_name],

        r = self.session.post(self.api_url, data=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            if data['error']['code'] == 'cantdelete':
                raise CanNotDelete(data['error']['info'])
            raise MediaWikiAPIError(data['error'])

    def edit_page(
            self, page_name: str, text: str, summary: Optional[str] = None
    ) -> None:
        """Delete page."""
        params: Dict[str, Any] = {
            'action': 'edit',
            'title': page_name,
            'text': text,
            'format': 'json',
        }
        if summary is not None:
            params['summary'] = summary
        if page_name not in self.edit_tokens:
            self.edit_tokens.update(self.get_tokens('edit', page_name))
        params['token'] = self.edit_tokens[page_name],

        r = self.session.post(self.api_url, data=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            if data['error']['code'] == 'protectedpage':
                raise PageProtected(data['error'])
            raise MediaWikiAPIError(data['error'])

    def upload_file(
        self, file_name: str, file: BinaryIO, mime_type: Optional[str],
        text: Optional[str] = None, ignore_warnings: bool = True
    ) -> None:
        """Upload file."""
        raise NotImplementedError()

    def get_tokens(self, token_type: str, titles: str) -> Dict[str, str]:
        """Return page tokens for API."""
        params: Dict[str, Any] = {
            'action': 'query',
            'prop': 'info',
            'titles': titles,
            'intoken': token_type,
            'format': 'json',
        }

        r = self.session.post(self.api_url, data=params)
        if r.status_code != 200:
            raise StatusCodeError(r.status_code)

        data = r.json()
        if 'error' in data:
            raise MediaWikiAPIError(data['error'])
        if 'warning' in data:
            raise MediaWikiAPIError(data['warning'])

        return dict(map(
            lambda page_data: (
                    page_data['title'], page_data['{}token'.format(token_type)]
                    ),
            data['query']['pages'].values()
        ))

    def get_backlinks(
        self, title: str, namespace: Optional[int], limit: int
    ) -> Iterator[Dict[str, Any]]:
        """Get list of pages which has links to given page."""
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'backlinks',
            'bltitle': title,
            'bllimit': limit,
            'format': 'json',
        }
        if namespace is not None:
            params['blnamespace'] = namespace

        last_continue: Dict[str, Any] = {}

        while True:
            current_params = params.copy()
            current_params.update(last_continue)
            r = self.session.get(self.api_url, params=current_params)
            if r.status_code != 200:
                raise StatusCodeError(r.status_code)

            data = r.json()
            if 'error' in data:
                raise MediaWikiAPIError(data['error'])
            backlinks = data['query']['backlinks']

            for backlink in backlinks:
                yield backlink

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['backlinks']

    def api_login(self, username: str, password: str) -> None:
        """Log in to MediaWiki API."""
        params1: Dict[str, Any] = {
            'action': 'login',
            'format': 'json',
            'lgname': username,
            'lgpassword': password,
        }

        r1 = self.session.post(self.api_url, params1)
        if r1.status_code != 200:
            raise StatusCodeError(r1.status_code)

        data1 = r1.json()
        if 'error' in data1:
            raise MediaWikiAPIError(data1['error'])
        if 'warning' in data1:
            raise MediaWikiAPIError(data1['warning'])

        if data1['login']['result'] == 'Success':
            return

        if data1['login']['result'] != 'NeedToken':
            raise MediaWikiAPIError('Login result is {}'.format(
                data1['login']['result']
            ))

        params2: Dict[str, Any] = {
            'action': 'login',
            'format': 'json',
            'lgname': username,
            'lgpassword': password,
            'lgtoken': data1['login']['token'],
        }

        r2 = self.session.post(self.api_url, data=params2)
        if r2.status_code != 200:
            raise MediaWikiAPIError('Status code is {}'.format(r2.status_code))

        data2 = r2.json()
        if 'error' in data2:
            raise MediaWikiAPIError(data2['error'])
        if 'warning' in data2:
            raise MediaWikiAPIError(data2['warning'])

        if data2['login']['result'] != 'Success':
            raise MediaWikiAPIError('Login result is {}'.format(
                data2['login']['result']
            ))


class MediaWikiAPI1_31(MediaWikiAPI):
    """MediaWiki API 1.31 class with authentication data."""

    api_url: str
    index_url: str
    session: requests.Session
    csrf_token: Optional[str]

    def __init__(self, url: str):
        """Create MediaWiki API 1.31 class with given API URL."""
        self.api_url = '{}/api.php'.format(url)
        self.index_url = '{}/index.php'.format(url)
        self.session = requests.Session()
        self.csrf_token = None

    def get_namespace_list(self) -> List[int]:
        """Iterate over namespaces in wiki."""
        params: Dict[str, Any] = {
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
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over user edits.

        Iterate over all edits made by `user in `namespace` since `start_date`
        until `end_date`.
        """
        params: Dict[str, Any] = {
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
        last_continue: Dict[str, Any] = {}

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
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'allimages',
            'aidir': 'ascending',
            'ailimit': limit,
            'format': 'json',
        }
        last_continue: Dict[str, Any] = {}

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
        params: Dict[str, Any] = {
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
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over pages in category `category_name`.

        `member_type` can be `None`, `page`, 'subcat` or `file`.
        """
        params: Dict[str, Any] = {
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
        last_continue: Dict[str, Any] = {}

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
        params: Dict[str, Any] = {
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
        last_continue: Dict[str, Any] = {}

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
        params: Dict[str, Any] = {
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
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'search',
            'srnamespace': namespace,
            'srlimit': limit,
            'format': 'json',
            'srsearch': search_request,
            'srwhat': 'text',
        }
        last_continue: Dict[str, Any] = {}

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
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over deleted revisions in wiki in `namespace`."""
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'deletedrevs',  # TODO: deprecated since MediaWiki 1.25
            'drnamespace': namespace,
            'drdir': 'newer',
            'drlimit': limit,
            'drprop': 'revid|user|comment|content',
            'format': 'json',
        }
        last_continue: Dict[str, Any] = {}

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
        params: Dict[str, Any] = {
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
        params: Dict[str, Any] = {
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

        params: Dict[str, Any] = {
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
            raise MediaWikiAPIError(data['error'])

    def get_token(self, token_type: str) -> str:
        """Return CSRF token for API."""
        params: Dict[str, Any] = {
            'action': 'query',
            'meta': 'tokens',
            'type': token_type,
            'format': 'json',
        }

        data = self.call_api(params)

        return data['query']['tokens']['{}token'.format(token_type)]

    def get_backlinks(
        self, title: str, namespace: Optional[int], limit: int
    ) -> Iterator[Dict[str, Any]]:
        """Get list of pages which has links to given page."""
        params: Dict[str, Any] = {
            'action': 'query',
            'list': 'backlinks',
            'bltitle': title,
            'bllimit': limit,
            'format': 'json',
        }
        if namespace is not None:
            params['blnamespace'] = namespace

        last_continue: Dict[str, Any] = {}

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
                raise MediaWikiAPIError(data['error'])
            backlinks = data['query']['backlinks']

            for backlink in backlinks:
                yield backlink

            if 'query-continue' not in data:
                break
            last_continue = data['query-continue']['backlinks']

    def api_login(self, username: str, password: str) -> None:
        """Log in to MediaWiki API."""
        token = self.get_token('login')

        params: Dict[str, Any] = {
            'action': 'login',
            'format': 'json',
            'lgname': username,
            'lgpassword': password,
            'lgtoken': token,
        }

        self.call_api(params, is_post=True, need_token=False)

    def call_api(
        self, params: Dict[str, Any], is_post: bool = False,
        need_token: bool = False, token_retry: bool = True
    ) -> Dict[str, Any]:
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

            data: Dict[str, Any] = r.json()
            if 'error' in data:
                if need_token and token_retry:
                    if data['error']['code'] == 'badtoken':
                        self.csrf_token = self.get_token('csrf')
                        continue
                if data['error']['code'] == 'cantdelete':
                    raise CanNotDelete(data['error']['info'])
                raise MediaWikiAPIError(data['error']['info'])

            return data
