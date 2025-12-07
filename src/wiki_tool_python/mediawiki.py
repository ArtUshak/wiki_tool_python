"""MediaWiki API interaction functions."""

import datetime
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import BinaryIO

import click

NAMESPACE_IMAGES = 6


class MediaWikiAPIError(click.ClickException):
    """MediaWiki API error."""


class StatusCodeError(MediaWikiAPIError):
    """Status code is not OK."""

    url: str
    status_code: int

    def __init__(self, url: str, status_code: int) -> None:
        """Initialize."""
        self.url = url
        self.status_code = status_code
        super().__init__(f"Request to {url} returned status code {status_code}")


class CanNotDeleteError(MediaWikiAPIError):
    """Page can not be deleted."""


class PageProtectedError(MediaWikiAPIError):
    """Page can not be edited because it is protected."""


class LoginMiscError(MediaWikiAPIError):
    """Misc login error."""

    login_result: str

    def __init__(self, login_result: str) -> None:
        """Initialize."""
        self.login_result = login_result
        super().__init__(f"Login result is {login_result}")


class MediaWikiAPIMiscError(MediaWikiAPIError):
    """MediaWiki API error."""

    data: object

    def __init__(self, data: object) -> None:
        """Initialize."""
        self.data = data
        super().__init__(str(data))


class MediaWikiAPI(ABC):
    """Base MediaWiki API class."""

    @abstractmethod
    def get_namespace_list(self) -> Iterable[int]:
        """Get iterable of all namespaces in wiki."""
        raise NotImplementedError

    @abstractmethod
    def get_user_contributions_list(
        self,
        namespace: int,
        limit: int,
        user: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> Iterator[dict[str, object]]:
        """
        Iterate over user edits.

        Iterate over all edits made by `user in `namespace` since `start_date`
        until `end_date`.
        """
        raise NotImplementedError

    @abstractmethod
    def get_image_list(self, limit: int) -> Iterator[dict[str, str]]:
        """
        Iterate over all images in wiki.

        Each image data is dictionary with two fields: `title` and `url`.
        """
        raise NotImplementedError

    def get_page_image_list(
        self, image_ids_limit: int, page_ids: list[int]
    ) -> Iterator[dict[str, str]]:
        """Iterate over images with given page IDs."""
        raise NotImplementedError

    @abstractmethod
    def get_category_members(
        self,
        category_name: str,
        limit: int,
        namespace: int | None = None,
        member_type: str | None = None,
    ) -> Iterator[dict[str, object]]:
        """Iterate over pages in category `category_name`."""
        raise NotImplementedError

    @abstractmethod
    def get_page_list(
        self,
        namespace: int,
        limit: int,
        first_page: str | None = None,
        redirect_filter_mode: str = "all",
    ) -> Iterator[str]:
        """Iterate over all page names in wiki in `namespace`."""
        raise NotImplementedError

    @abstractmethod
    def get_page(
        self,
        title: str,
    ) -> str:
        """Get text of page with `title`."""
        raise NotImplementedError

    @abstractmethod
    def search_pages(
        self,
        search_request: str,
        namespace: int,
        limit: int,
    ) -> Iterator[str]:
        """Search pages in wiki in `namespace` with `search_request`."""
        raise NotImplementedError

    @abstractmethod
    def get_deletedrevs_list(
        self, namespace: int, limit: int
    ) -> Iterator[dict[str, object]]:
        """Iterate over deleted revisions in wiki in `namespace`."""
        raise NotImplementedError

    @abstractmethod
    def upload_file(
        self,
        file_name: str,
        file: BinaryIO,
        mime_type: str | None,
        text: str | None = None,
        ignore_warnings: bool = True,
    ) -> None:
        """Upload file."""
        raise NotImplementedError

    @abstractmethod
    def delete_page(self, page_name: str, reason: str | None = None) -> None:
        """Delete page."""
        raise NotImplementedError

    @abstractmethod
    def edit_page(
        self, page_name: str, text: str, summary: str | None = None
    ) -> None:
        """Edit page, setting new text."""
        raise NotImplementedError

    @abstractmethod
    def get_backlinks(
        self, title: str, namespace: int | None, limit: int
    ) -> Iterator[dict[str, object]]:
        """Get list of pages which has links to given page."""
        raise NotImplementedError

    @abstractmethod
    def api_login(self, username: str, password: str) -> None:
        """Log in to MediaWiki API."""
        raise NotImplementedError
