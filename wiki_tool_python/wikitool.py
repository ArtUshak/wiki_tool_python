# -*- coding: utf-8 -*-
"""Script for interacting with MediaWiki."""
import contextlib
import copy
import datetime
import itertools
import json
import mimetypes
import os
import pathlib
import re
import shlex
import shutil
import unicodedata
from typing import (BinaryIO, ContextManager, Dict, Iterable, Iterator, List,
                    Optional, TextIO, Tuple)

import click
import requests

import mediawiki
from mediawiki_1_19 import MediaWikiAPI1_19
from mediawiki_1_31 import MediaWikiAPI1_31


def read_image_list(image_list_file: TextIO) -> Iterator[Dict[str, str]]:
    """
    Iterate over image data listed in file `image_list_file`.

    Each image data is dictionary with two fields: `name` and `url`.
    """
    file_iterator = iter(image_list_file)
    try:
        while True:
            header_line = next(file_iterator)
            title_line = next(file_iterator)
            url_line = next(file_iterator)
            filename_line = next(file_iterator)
            if header_line.strip() != 'FILE2':
                raise ValueError()  # TODO
            yield {
                'name': title_line.strip(),
                'url': url_line.strip(),
                'filename': filename_line.strip(),
            }
    except StopIteration:
        pass


@click.group()
@click.option(
    '--credentials', type=click.STRING,
    help='LOGIN:PASSWORD pair for MediaWiki'
)
@click.option(
    '--login/--no-login', default=False,
    help='Log in even for method that do not require authentication'
)
@click.option(
    '--mediawiki-version', default='1.31', type=click.STRING,
    help='MediaWiki version, default is 1.31'
)
@click.option(
    '--requests-interval', type=click.FloatRange(min=0.0),
    help='Delay between requests'
)
@click.option(
    '--user-agent', type=click.STRING, default='WikiToolPython',
    help='User-Agent value'
)
@click.pass_context
def cli(
    ctx: click.Context, credentials: Optional[str], login: bool,
    mediawiki_version: Optional[str], requests_interval: Optional[float],
    user_agent: str
):
    """Run MediaWiki script for exporting data and downloading images."""
    ctx.ensure_object(dict)

    credentials_list: List[str] = []
    if credentials is not None:
        credentials_list = credentials.split(':')
        if len(credentials_list) != 2:
            raise click.ClickException('Bad credentials format')
        ctx.obj['MEDIAWIKI_CREDENTIALS'] = tuple(credentials_list)
    elif 'MEDIAWIKI_CREDENTIALS' in os.environ:
        credentials = os.environ['MEDIAWIKI_CREDENTIALS']
        credentials_list = credentials.split(':')
        if len(credentials_list) != 2:
            raise click.ClickException('Bad credentials format')
        ctx.obj['MEDIAWIKI_CREDENTIALS'] = tuple(credentials_list)

    ctx.obj['MEDIAWIKI_VERSION'] = mediawiki_version
    ctx.obj['MEDIAWIKI_SHOULD_LOGIN'] = login
    ctx.obj['REQUESTS_INTERVAL'] = requests_interval or 0.0
    ctx.obj['USER_AGENT'] = user_agent


def get_mediawiki_api_without_login(
    mediawiki_version: str, api_url: str, request_interval: float,
    user_agent: str
) -> mediawiki.MediaWikiAPI:
    """
    Return MediaWiki API object for given version and API URL.

    Raise exception if version is not implemented.
    """
    if mediawiki_version == '1.31':
        return MediaWikiAPI1_31(api_url, request_interval, user_agent)
    if mediawiki_version == '1.19':
        return MediaWikiAPI1_19(api_url, request_interval, user_agent)
    raise click.ClickException(
        'MediaWiki API version {} is not yet implemented'.format(
            mediawiki_version
        )
    )


def get_mediawiki_api(
    ctx: click.Context, api_url: str, request_interval: float
) -> mediawiki.MediaWikiAPI:
    """
    Return MediaWiki API object for given version and API URL.

    Raise exception if version is not implemented.
    Log in if required by user.
    """
    api = get_mediawiki_api_without_login(
        ctx.obj['MEDIAWIKI_VERSION'], api_url, ctx.obj['REQUESTS_INTERVAL'],
        ctx.obj['USER_AGENT']
    )

    if ctx.obj['MEDIAWIKI_SHOULD_LOGIN']:
        if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
            raise click.ClickException('User credentials not given')
        user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']
        api.api_login(user_credentials[0], user_credentials[1])

    return api


def get_mediawiki_api_with_auth(
    ctx: click.Context, api_url: str
) -> mediawiki.MediaWikiAPI:
    """
    Return MediaWiki API object for given version and API URL.

    Return `None` if version is not implemented
    """
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api_without_login(
        ctx.obj['MEDIAWIKI_VERSION'], api_url, ctx.obj['REQUESTS_INTERVAL'],
        ctx.obj['USER_AGENT']
    )
    api.api_login(user_credentials[0], user_credentials[1])
    return api


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.option(
    '--output-file', type=click.File('wt'),
    help='Text file to write image list'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
@click.option(
    '--confine-encoding', default=None, type=click.STRING,
    help=(
        'Encoding to confine file name to '
        '(drop characters outside that encoding)'
    )
)
def list_images(
    ctx: click.Context, api_url: str, output_file: TextIO, api_limit: int,
    confine_encoding: Optional[str]
):
    """List images from wikiproject (titles and URLs)."""
    api = get_mediawiki_api(ctx, api_url, ctx.obj['REQUESTS_INTERVAL'])
    i: int = 0
    for image in api.get_image_list(api_limit):
        title_regex = re.match(r'.+?\:(.*)', image['title'])
        if title_regex is None:
            raise ValueError()  # TODO
        title: str = title_regex.group(1)
        filename: str = get_safe_filename(title, i)
        if confine_encoding is not None:
            title = confine_to_encoding(title, confine_encoding)
            filename = confine_to_encoding(filename, confine_encoding)
        url: str = image['url']
        click.echo(
            'FILE2\n{}\n{}\n{}'.format(title, url, filename),
            file=output_file
        )
        i += 1


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('category', type=click.STRING)
@click.option(
    '--output-file', type=click.File('wt', encoding='utf-8'),
    help='Text file to write image list'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
@click.option(
    '--api-image-ids-limit', default=50, type=click.INT,
    help='Maximum number of image IDs passed per API request'
)
@click.option(
    '--confine-encoding', default=None, type=click.STRING,
    help=(
        'Encoding to confine file name to '
        '(drop characters outside that encoding)'
    )
)
def list_category_images(
    ctx: click.Context, api_url: str, category: str, output_file: TextIO,
    api_limit: int, api_image_ids_limit: int, confine_encoding: Optional[str]
):
    """List images from category (titles and URLs)."""
    api = get_mediawiki_api(ctx, api_url, ctx.obj['REQUESTS_INTERVAL'])
    page_ids: List[int] = list(map(
        lambda page_data: page_data['pageid'],
        api.get_category_members(
            category, api_limit, mediawiki.NAMESPACE_IMAGES, 'file'
        )
    ))
    i: int = 0
    with click.progressbar(
        api.get_page_image_list(api_image_ids_limit, page_ids),
        length=len(page_ids)
    ) as bar:
        for image_data in bar:
            title_regex = re.match(r'.+?\:(.*)', image_data['title'])
            if title_regex is None:
                raise ValueError()  # TODO
            title: str = title_regex.group(1)
            filename: str = get_safe_filename(title, i)
            if confine_encoding is not None:
                title = confine_to_encoding(title, confine_encoding)
                filename = confine_to_encoding(filename, confine_encoding)
            url: str = image_data['url']
            click.echo(
                'FILE2\n{}\n{}\n{}'.format(title, url, filename),
                file=output_file
            )
            i += 1


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.option(
    '--output-file', type=click.File('wt', encoding='utf-8'),
    help='Text file to write page list'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
def list_pages(
    ctx: click.Context, api_url: str, output_file: TextIO, api_limit: int
):
    """List page names from wikiproject."""
    api = get_mediawiki_api(ctx, api_url, ctx.obj['REQUESTS_INTERVAL'])
    for namespace in api.get_namespace_list():
        for page_name in api.get_page_list(
            namespace, api_limit
        ):
            click.echo(
                page_name,
                file=output_file
            )


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('namespace', type=click.INT)
@click.option(
    '--output-file', type=click.File('wt', encoding='utf-8'),
    help='Text file to write page list'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
def list_namespace_pages(
    ctx: click.Context, api_url: str, namespace: int, output_file: TextIO,
    api_limit: int
):
    """List page names from wikiproject."""
    api = get_mediawiki_api(ctx, api_url, ctx.obj['REQUESTS_INTERVAL'])
    for page_name in api.get_page_list(
        namespace, api_limit
    ):
        click.echo(
            page_name,
            file=output_file
        )


@click.command()
@click.pass_context
@click.argument(
    'output_directory', type=click.Path(file_okay=False, dir_okay=True)
)
@click.argument('api_url', type=click.STRING)
@click.option(
    '--all-namespaces', default=False, type=click.BOOL,
    help='TRUE to list for all namespaces, FALSE for main namespace only'
)
@click.option(
    '--file-entry-num', default=500, type=click.INT,
    help='Number of entries per JSON file'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
def list_deletedrevs(
    ctx: click.Context, output_directory: str, api_url: str,
    all_namespaces: bool, file_entry_num: int, api_limit: int
):
    """List deleted revision from wikiproject in JSON format."""
    output_directory_path = pathlib.Path(output_directory)

    api = get_mediawiki_api_with_auth(ctx, api_url)

    file_number = 0

    namespaces: Iterable[int] = [0]
    if all_namespaces:
        namespaces = api.get_namespace_list()

    for namespace in namespaces:
        chunk: List[Dict[str, object]] = []
        for revision in api.get_deletedrevs_list(
                namespace, api_limit
        ):
            chunk.append(revision)

            if len(chunk) == file_entry_num:
                output_file_path = output_directory_path.joinpath(
                    f'entry-{file_number}.json'
                )
                with open(
                    output_file_path, 'wt', encoding='utf-8'
                ) as output_file:
                    json.dump(
                        chunk,
                        output_file,
                        ensure_ascii=False
                    )

                chunk = []
                file_number += 1

    if len(chunk) > 0:
        output_file_path = output_directory_path.joinpath(
            f'entry-{file_number}.json'
        )
        with open(output_file_path, 'wt', encoding='utf-8') as output_file:
            json.dump(
                chunk,
                output_file,
                ensure_ascii=False
            )


@click.command()
@click.pass_context
@click.argument(
    'filter_expression', type=click.STRING
)
@click.argument('api_url', type=click.STRING)
@click.option(
    '--exclude-expression', type=click.STRING,
    help='Additional expression to exclude pages from deletion'
)
@click.option(
    '--first-page', type=click.STRING,
    help='First page to delete'
)
@click.option(
    '--first-page-namespace', type=click.INT,
    help='Namespace of first page to delete'
)
@click.option(
    '--reason', default='Mass deletion', type=click.STRING,
    help='Deletion reason'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
@click.option(
    '--namespace', type=click.INT, multiple=True,
    help='Page namespace', default=(0,)
)
def delete_pages(
    ctx: click.Context, filter_expression: str, api_url: str,
    exclude_expression: str,
    first_page: Optional[str], first_page_namespace: Optional[int],
    reason: str, api_limit: int, namespace: List[int]
):
    """Delete pages matching regular expression."""
    api = get_mediawiki_api_with_auth(ctx, api_url)

    if first_page_namespace is not None:
        namespace = namespace[namespace.index(first_page_namespace):]

    compiled_filter_expression = re.compile(filter_expression)

    compiled_exclude_expression = None
    if exclude_expression is not None:
        compiled_exclude_expression = re.compile(exclude_expression)

    deleted_num: int = 0
    failed_num: int = 0

    for namespace_item in namespace:
        for page_name in filter(
            lambda page_name:
            compiled_filter_expression.match(page_name) is not None,
            api.get_page_list(
                namespace_item, api_limit, first_page=first_page
            )
        ):
            if compiled_exclude_expression is not None:
                if compiled_exclude_expression.match(page_name):
                    continue
            try:
                api.delete_page(page_name, reason)
                click.echo(f'Deleted {page_name}')
                deleted_num += 1
            except mediawiki.CanNotDelete:
                click.echo(f'Can not delete {page_name}')
                failed_num += 1

    click.echo(f'{deleted_num} pages deleted')
    if failed_num > 0:
        click.echo(f'{deleted_num} pages not deleted')


@click.command()
@click.pass_context
@click.argument(
    'filter_expression', type=click.STRING
)
@click.argument(
    'new_text', type=click.STRING
)
@click.argument('api_url', type=click.STRING)
@click.option(
    '--exclude-expression', type=click.STRING,
    help='Additional expression to exclude pages from editing'
)
@click.option(
    '--first-page', type=click.STRING,
    help='First page to edit'
)
@click.option(
    '--first-page-namespace', type=click.INT,
    help='Namespace of first page to edit'
)
@click.option(
    '--reason', default='Mass edit', type=click.STRING,
    help='Edit reason'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
@click.option(
    '--namespace', type=click.INT, multiple=True,
    help='Page namespace', default=(0,)
)
def edit_pages(
    ctx: click.Context, filter_expression: str, new_text: str,
    api_url: str, exclude_expression: str,
    first_page: Optional[str], first_page_namespace: Optional[int],
    reason: str, api_limit: int, namespace: List[int]
):
    """Edit pages matching filter expression, using new text."""
    api = get_mediawiki_api_with_auth(ctx, api_url)

    if first_page_namespace is not None:
        namespace = namespace[namespace.index(first_page_namespace):]

    compiled_filter_expression = re.compile(filter_expression)
    exclude_filter_expression = None
    if exclude_expression is not None:
        exclude_filter_expression = re.compile(exclude_expression)

    edited_num: int = 0

    for namespace_item in namespace:
        for page_name in filter(
            lambda page_name:
            compiled_filter_expression.match(page_name) is not None,
            api.get_page_list(
                namespace_item, api_limit, redirect_filter_mode='nonredirects',
                first_page=first_page
            )
        ):
            if exclude_filter_expression is not None:
                if exclude_filter_expression.match(page_name):
                    continue
            api.edit_page(page_name, new_text, reason)
            click.echo(f'Edited {page_name}')
            edited_num += 1

    click.echo(f'{edited_num} pages edited')


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('old', type=click.STRING)
@click.argument('new', type=click.STRING)
@click.option(
    '--reason', default='Mass interwiki fix', type=click.STRING,
    help='Edit reason'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
def edit_pages_clone_interwikis(
    ctx: click.Context, api_url: str, old: str, new: str,
    reason: str, api_limit: int,
):
    """Add interwiki NEW to pages that contain interwiki OLD but not NEW."""
    api = get_mediawiki_api_with_auth(ctx, api_url)

    search_request = old

    expr_old = re.compile(
        r'(^.*\[\[' + old + r'\:(.+?)\]\])',
        flags=re.MULTILINE | re.DOTALL
    )
    expr_new = re.compile(
        r'^.*\[\[' + new + r'\:(.+?)\]\]',
        flags=re.MULTILINE | re.DOTALL
    )

    edited_num: int = 0

    for namespace in api.get_namespace_list():
        for page_name in api.search_pages(
            search_request, namespace, api_limit
        ):
            text = api.get_page(page_name)
            regex_new_result = expr_new.match(text)
            if regex_new_result is not None:
                continue
            regex_old_result = expr_old.match(text)
            if regex_old_result is None:
                continue
            new_text = expr_old.sub(r'\1\n[[{}:\2]]'.format(new), text)
            api.edit_page(page_name, new_text, reason)
            click.echo(f'Edited {page_name}')
            edited_num += 1

    click.echo(f'{edited_num} pages edited')


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('old', type=click.STRING)
@click.argument('new', type=click.STRING)
@click.option(
    '--reason', default='Replacing links', type=click.STRING,
    help='Edit reason'
)
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
def replace_links(
    ctx: click.Context, api_url: str, old: str, new: str,
    reason: str, api_limit: int,
):
    """Replace links to page OLD by links to page NEW."""
    api = get_mediawiki_api_with_auth(ctx, api_url)

    edited_num: int = 0
    processed_num: int = 0
    protected_num: int = 0

    backlinks = list(api.get_backlinks(old, None, api_limit))

    with click.progressbar(backlinks, length=len(backlinks)) as bar:
        for backlink in bar:
            page_name = backlink['title']
            old_text = api.get_page(page_name)
            new_text1 = re.sub(
                r'\[\[' + old + r'\|([^\]]+)\]\]',
                lambda m: '[[' + new + '|' + m.group(1) + ']]',
                old_text,
                flags=re.I
            )
            new_text2 = re.sub(
                r'\[\[(' + old + r')\]\]',
                lambda m: '[[' + new + '|' + m.group(1) + ']]',
                new_text1,
                flags=re.I
            )
            processed_num += 1
            if old_text == new_text2:
                continue
            try:
                api.edit_page(page_name, new_text2, reason)
            except mediawiki.PageProtected:
                protected_num += 1
                continue
            edited_num += 1

    click.echo(
        f'{processed_num} pages processed, {edited_num} pages edited, '
        f'{protected_num} were not edited due to protection level'
    )


def confine_to_encoding(value: str, confine_encoding: str) -> str:
    """Convert string to encoding, drop invalid characters and convert back."""
    return value.encode(
        confine_encoding, errors='ignore'
    ).decode(confine_encoding)


def get_safe_filename(value: str, i: int) -> str:
    """
    Transform file name so it will be NTFS-compliant.

    Add `i` to file name (to beginning), remove illegal characters and
    leading and trailing whitespaces.
    """
    value = unicodedata.normalize('NFKC', '{:05}-{}'.format(i, value.strip()))
    return re.sub(r'[\<\>\:\"\/\\\|\?\*]', '', value).strip()


@click.command()
@click.pass_context
@click.argument('list_file', type=click.File('rt'))
@click.argument(
    'download_dir', type=click.Path(file_okay=False, dir_okay=True)
)
def download_images(ctx: click.Context, list_file: TextIO, download_dir: str):
    """Download images listed in file."""
    download_dir_path = pathlib.Path(download_dir)

    with click.progressbar(list(read_image_list(list_file))) as bar:
        for image in bar:
            r = requests.get(image['url'], stream=True)
            if r.status_code == 200:
                image_filename = download_dir_path.joinpath(image['filename'])
                with open(image_filename, 'wb') as image_file:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, image_file)
            elif r.status_code != 404:
                click.echo(
                    'Failed to download URL {} (status code: {}).'.format(
                        r.url, r.status_code
                    )
                )


@click.command()
@click.pass_context
@click.argument(
    'file_name', type=click.STRING
)
@click.argument(
    'file', type=click.File('rb')
)
@click.argument('api_url', type=click.STRING)
def upload_image(
    ctx: click.Context, file_name: str, file: BinaryIO, api_url: str,
):
    """Upload image."""
    api = get_mediawiki_api_with_auth(ctx, api_url)

    api.upload_file(
        file_name, file, mimetypes.guess_type(file.name)[0]  # TODO
    )


@click.command()
@click.pass_context
@click.argument('list_file', type=click.File('rt'))
@click.argument(
    'download_dir', type=click.Path(file_okay=False, dir_okay=True)
)
@click.argument('api_url', type=click.STRING)
@click.option(
    '--skip-nonexistent/--no-skip-nonexistent', default=True,
    help='Do not fail on non-existent files, skip them instead'
)
def upload_images(
    ctx: click.Context, list_file: TextIO, download_dir: str, api_url: str,
    skip_nonexistent: bool
):
    """Upload images listed in file."""
    download_dir_path = pathlib.Path(download_dir)

    api = get_mediawiki_api_with_auth(ctx, api_url)

    skipped_filenames: List[str] = []

    with click.progressbar(list(read_image_list(list_file))) as bar:
        for image in bar:
            image_name: str = image['name']
            image_filename = download_dir_path.joinpath(
                image['filename']
            )
            if not image_filename.exists():
                if skip_nonexistent:
                    click.echo(f'File {image_name} not found')
                    skipped_filenames.append(image_name)
                    continue
                else:
                    raise click.ClickException(f'File {image_name} not found')
            with open(image_filename, 'rb') as image_file:
                try:
                    api.upload_file(
                        image_name, image_file,
                        mimetypes.guess_type(image_name)[0]
                    )
                except mediawiki.MediaWikiAPIError as exc:
                    click.echo(
                        'Failed to upload file {}: {}.'.format(
                            image_name, str(exc)
                        )
                    )
                except FileNotFoundError:
                    if skip_nonexistent:
                        click.echo('Warning')

    if len(skipped_filenames):
        click.echo('Skipped (non-existent) files:')
        for skipped_filename in skipped_filenames:
            click.echo(skipped_filename)


def read_user_data(input_file: TextIO) -> List[str]:
    """Read user list from text file."""
    users = map(lambda s: s.strip(), input_file.readlines())
    return list(users)


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('user_list_file', type=click.File('rt'))
@click.option('--namespacefile', default='namespaces.json',
              type=click.File('rt'),
              help='JSON file to read namespaces data from')
@click.option('--start',
              type=click.DateTime(),
              help='Start date for counting edits')
@click.option('--end',
              type=click.DateTime(),
              help='End date for counting edits')
@click.option('--output-format', default='mediawiki',
              type=click.Choice(['txt', 'mediawiki', 'json']),
              help='Output data format')
@click.option('--redirect-regex-text',
              default=r'^Redirect to \[\[.+\]\]$', type=click.STRING,
              help='Regular expression to detect redirect creation')
@click.option(
    '--api-limit', default=500, type=click.INT,
    help='Maximum number of entries per API request'
)
def votecount(
    ctx: click.Context, api_url: str, user_list_file: TextIO,
    namespacefile: TextIO, start: datetime.datetime, end: datetime.datetime,
    output_format: str, api_limit: int, redirect_regex_text: str,
):
    """Get edit counts for users from input file, and calculate vote power."""
    api = get_mediawiki_api(ctx, api_url, ctx.obj['REQUESTS_INTERVAL'])

    regex_redirect = re.compile(redirect_regex_text)

    users = read_user_data(user_list_file)

    namespaces_raw = json.load(namespacefile)
    if not isinstance(namespaces_raw, dict):
        raise ValueError()  # TODO
    namespaces_edit_weights = namespaces_raw['edit_weights']
    namespaces_edit_weights = dict(
        map(lambda key: (int(key), namespaces_edit_weights[key]),
            namespaces_edit_weights))
    namespaces_page_weights = namespaces_raw['page_weights']
    namespaces_page_weights = dict(
        map(lambda key: (int(key), namespaces_page_weights[key]),
            namespaces_page_weights))

    users_data: Dict[str, Dict[str, object]] = {}
    for user in users:
        click.echo('Processing user {}...'.format(user))
        user_vote_power: float = 0.0
        user_new_pages: int = 0
        user_data: Dict[str, object] = {}

        for namespace in namespaces_edit_weights:
            pages_count = 0
            edit_count = 0

            for contrib in api.get_user_contributions_list(
                namespace, api_limit, user, start, end
            ):
                edit_count += 1
                if (('new' in contrib)
                        and (regex_redirect.match(contrib['comment'])
                             is None)):
                    pages_count += 1

            user_data[namespace] = edit_count

            user_vote_power += (edit_count
                                * namespaces_edit_weights[namespace])

            if namespace in namespaces_page_weights:
                user_new_pages += pages_count
                user_vote_power += (pages_count
                                    * namespaces_page_weights[namespace])

        user_data['NewPages'] = user_new_pages
        user_data['VotePower'] = user_vote_power
        users_data[user] = copy.copy(user_data)

    if output_format == 'txt':
        for user in users_data:
            click.echo(f'User {user}')
            for key in user_data:
                click.echo('{}: {}'.format(key, user_data[key]))
            click.echo('')
    elif output_format == 'json':
        click.echo(json.dumps(users_data))
    elif output_format == 'mediawiki':
        click.echo('{| class="wikitable"')
        click.echo(' ! Участник')
        for namespace in namespaces_edit_weights:
            click.echo(f' ! N{namespace}')
        click.echo(' ! A')
        click.echo(' ! Сила голоса (автоматическая)')
        click.echo(' ! Сила голоса (итоговая)')
        for user in users_data:
            click.echo(' |-')
            click.echo(f' | {{{{ U|{user} }}}}')
            for key in namespaces_edit_weights:
                click.echo(' | style="text-align: right;" | {}'.format(
                    users_data[user][key]))
            click.echo(' | style="text-align: right;" | {}'.format(
                users_data[user]['NewPages']))
            click.echo(' | style="text-align: right;" | {:.4}'.format(
                users_data[user]['VotePower']))
            click.echo(' | style="text-align: right;" | ?')
        click.echo(' |}')
    else:
        for user in users_data:
            click.echo('User {}'.format(user))
            for key in namespaces_edit_weights:
                click.echo('N{}: {}'.format(key, users_data[user][key]))
            click.echo('NewPages: {}'.format(users_data[user]['NewPages']))
            click.echo(
                'VotePower: {:.4}'.format(users_data[user]['VotePower']))
            click.echo('')


def get_directory_page_list(
    root_directory_path: pathlib.Path, input_directory_path: pathlib.Path,
    show_progess: bool
) -> List[pathlib.Path]:
    """List `.txt` files in directory recursively."""
    result: List[pathlib.Path] = []
    it = input_directory_path.iterdir()
    ctx: ContextManager[Iterable[pathlib.Path]]
    if show_progess:
        ctx = click.progressbar(
            iter(it), length=len(os.listdir(str(input_directory_path)))
        )
    else:
        ctx = contextlib.nullcontext(iter(it))
    with ctx as it1:
        for input_file_path in it1:
            if input_file_path.is_dir():
                result += get_directory_page_list(
                    root_directory_path, input_file_path, False
                )
            elif input_file_path.is_file():
                if input_file_path.suffix != '.txt':
                    continue
                result.append(
                    input_file_path.relative_to(root_directory_path)
                )
    return result


@click.command()
@click.argument(
    'input_directory',
    type=click.Path(
        exists=True, readable=True, dir_okay=True, file_okay=False
    )
)
@click.argument(
    'output_file',
    type=click.File(mode='wt', encoding='utf-8')
)
def list_directory_pages(input_directory: str, output_file: TextIO):
    """Write list of `.txt` file pathes in directory to JSON file."""
    input_directory_path = pathlib.Path(input_directory)
    page_file_list = get_directory_page_list(
        input_directory_path, input_directory_path, True
    )
    json.dump(
        list(map(str, page_file_list)), output_file,
        ensure_ascii=False, indent=4
    )


def get_progress_bar_text(
    total_count: int, current_count: int, width: int
) -> str:
    """Generate progress bar string."""
    filled_width: int = int(width * current_count / total_count)
    bar = '[' + '#' * filled_width + ' ' * (width - filled_width) + ']'
    label = f'{current_count: 9} / {total_count: 9}'
    return bar + ' ' + label


@click.command()
@click.argument(
    'list_file',
    type=click.File(mode='rt')
)
@click.argument(
    'input_directory',
    type=click.Path()
)
@click.argument(
    'output_script_file',
    type=click.File(mode='wt')
)
@click.argument(
    'log_file',
    type=click.Path()
)
@click.option(
    '--prefix', default='',
    type=click.STRING,
    help='Prefix for page titles'
)
@click.option(
    '--rc/--no-rc', default=True,
    help='Add --rc option to output script'
)
@click.option(
    '--bot/--no-bot', default=True,
    help='Add --bot option to output script'
)
@click.option(
    '--user', type=click.STRING,
    help='Add -u option to output script'
)
@click.option(
    '--summary', type=click.STRING,
    help='Add -s option to output script'
)
@click.option(
    '--maintenance-directory', default='maintenance',
    type=click.STRING,
    help='Directory with importTextFiles.php'
)
@click.option(
    '--show-progress-bar/--no-show-progress-bar', default=True,
    help='Add progress bar display to output script'
)
@click.option(
    '--first-page', type=click.INT,
    help='First page number'
)
def generate_import_script(
    list_file: TextIO, input_directory: str, output_script_file: TextIO,
    log_file: str, prefix: str, rc: bool, bot: bool, user: Optional[str],
    summary: Optional[str], maintenance_directory: str,
    show_progress_bar: bool, first_page: Optional[int]
):
    """
    Write script to import pages from list file using importTextFiles.php.
    """
    maintenance_directory_path = pathlib.Path(maintenance_directory)
    input_directory_path = pathlib.Path(input_directory)

    argv = [
        'php', str(maintenance_directory_path.joinpath('importTextFiles.php'))
    ]
    if rc:
        argv.append('--rc')
    if bot:
        argv.append('--bot')
    if user:
        argv += ['--user', user]
    if summary:
        argv += ['-s', summary]

    page_file_list = list(map(pathlib.Path, json.load(list_file)))
    current_directory_path = pathlib.Path('.')
    output_progress_bar_width = 20

    output_script_file.write('#!/bin/bash\n\n')

    current_file_count = 0
    total_file_count = len(page_file_list)
    with click.progressbar(page_file_list, show_pos=True) as bar:
        for page_file_path in bar:
            if first_page and (current_file_count < first_page):
                current_file_count += 1
                continue
            page_prefix: str
            if page_file_path.parent == current_directory_path:
                page_prefix = prefix
            else:
                page_prefix = prefix + str(page_file_path.parent) + '/'
            line_argv = argv + [
                '--prefix', page_prefix,
                str(input_directory_path.joinpath(page_file_path))
            ]
            output_script_file.write(
                shlex.join(line_argv)
                + ' >> ' + shlex.quote(log_file) + ' 2>&1 \n'
            )
            if show_progress_bar:
                progress_bar_text = get_progress_bar_text(
                    total_file_count, current_file_count + 1,
                    output_progress_bar_width
                )
                progress_line_argv = [
                    'echo', '-ne', progress_bar_text + '\\r'
                ]
                output_script_file.write(
                    shlex.join(progress_line_argv) + '\n'
                )
            current_file_count += 1


def upload_page_from_directory(
    api: mediawiki.MediaWikiAPI, input_directory_path: pathlib.Path,
    page_file_path: pathlib.Path, prefix: str, summary: Optional[str],
    append: bool, title: Optional[str]
):
    """
    Upload MediaWiki file as page with title according to path and prefix.

    Title can be also overwritten using `title` parameter, but prefix will be
    still applied.
    """
    with open(
        input_directory_path.joinpath(page_file_path), 'rt'
    ) as page_file:
        loaded_page_text = page_file.read()
    if title is None:
        page_title = prefix + str(page_file_path.with_suffix(''))
    else:
        page_title = prefix + title
    edit_page_text = loaded_page_text
    if append:
        try:
            old_page_text = api.get_page(page_title)
        except mediawiki.StatusCodeError as exc:
            if exc.status_code != 404:
                raise
        else:
            edit_page_text = (
                old_page_text + '\n\n' + edit_page_text
            )
    api.edit_page(
        page_title, edit_page_text, summary
    )


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument(
    'input_directory',
    type=click.Path(
        exists=True, readable=True, dir_okay=True, file_okay=False
    )
)
@click.argument(
    'list_file',
    type=click.File(mode='rt')
)
@click.option(
    '--dictionary/--no-dictionary', default=False,
    help='Use dictionary file of pathes and titles instead of file list'
)
@click.option(
    '--extended-dictionary/--no-extended-dictionary', default=False,
    help='Read dictionary values as dictionaries with "title" and "path" keys'
)
@click.option(
    '--prefix', default='',
    type=click.STRING,
    help='Prefix for page titles'
)
@click.option(
    '--summary', default='Mass upload', type=click.STRING,
    help='Edit summary'
)
@click.option(
    '--first-page', type=click.INT,
    help='Page number to start with'
)
@click.option(
    '--mode', default='append', type=click.Choice(
        ['append', 'overwrite']
    ),
    help=(
        'Whether to append text from file to old text on existing pages, '
        'or overwrite old text with text from file'
    )
)
@click.option(
    '--show-count/--no-show-count', default=False,
    help='Display uploaded page count'
)
def upload_pages(
    ctx: click.Context, api_url: str, input_directory: str, list_file: TextIO,
    dictionary: bool, extended_dictionary: str,
    prefix: str, summary: str, mode: str,
    first_page: Optional[int], show_count: bool
):
    """Create pages from txt files in input directory."""
    api = get_mediawiki_api_with_auth(ctx, api_url)

    input_directory_path = pathlib.Path(input_directory)

    if dictionary:
        file_data = json.load(list_file)
        if not isinstance(file_data, dict):
            raise ValueError()
        if extended_dictionary:
            page_file_list = list(map(
                lambda data: (data['title'], pathlib.Path(data['path'])),
                file_data.values()
            ))
        else:
            page_file_list = list(map(
                lambda data: (data[1], pathlib.Path(data[0])),
                file_data.items()
            ))
    else:
        file_data = json.load(list_file)
        if not isinstance(file_data, list):
            raise ValueError()
        page_file_list = list(map(
            lambda file_name: (None, pathlib.Path(file_name)),
            file_data
        ))

    append: bool
    if mode == 'append':
        append = True
    else:
        append = False

    length = len(page_file_list)
    it: Iterable[Tuple[Optional[str], pathlib.Path]] = page_file_list
    if first_page is not None:
        it = itertools.islice(it, first_page, None)
        length -= first_page
        if length < 0:
            length = 0

    uploaded_pages_count = 0
    with click.progressbar(it, show_pos=True, length=length) as bar:
        for page_title, page_file_path in bar:
            upload_page_from_directory(
                api, input_directory_path, page_file_path, prefix,
                summary, append, page_title
            )
            uploaded_pages_count += 1
    click.echo(f'Uploaded {uploaded_pages_count} pages')


cli.add_command(list_images)
cli.add_command(list_pages)
cli.add_command(list_category_images)
cli.add_command(list_namespace_pages)
cli.add_command(list_deletedrevs)
cli.add_command(download_images)
cli.add_command(delete_pages)
cli.add_command(edit_pages)
cli.add_command(edit_pages_clone_interwikis)
cli.add_command(replace_links)
cli.add_command(upload_image)
cli.add_command(upload_images)
cli.add_command(votecount)
cli.add_command(list_directory_pages)
cli.add_command(generate_import_script)
cli.add_command(upload_pages)


if __name__ == '__main__':
    # pylint: disable=unexpected-keyword-arg, no-value-for-parameter
    cli(obj={})
