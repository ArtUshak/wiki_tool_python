# -*- coding: utf-8 -*-
"""Script for interacting with MediaWiki."""
import copy
import datetime
import json
import mimetypes
import os
import re
import shutil
import unicodedata
from typing import (Any, BinaryIO, Dict, Iterable, Iterator, List, Optional,
                    TextIO, Tuple)

import click
import requests

from wiki_tool_python import mediawiki


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
                raise ValueError()
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
    '--mediawiki-version', default='1.31', type=click.STRING,
    help='MediaWiki version, default is 1.31'
)
@click.pass_context
def cli(
    ctx: click.Context, credentials: Optional[str],
    mediawiki_version: Optional[str]
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


def get_mediawiki_api(
    mediawiki_version: str, api_url: str
) -> mediawiki.MediaWikiAPI:
    """
    Return MediaWiki API object for given version and API URL.

    Return `None` if version is not implemented
    """
    if mediawiki_version == '1.31':
        return mediawiki.MediaWikiAPI1_31(api_url)
    if mediawiki_version == '1.19':
        return mediawiki.MediaWikiAPI1_19(api_url)
    raise click.ClickException(
        'MediaWiki API version {} is not yet implemented'.format(
            mediawiki_version
        )
    )


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
def list_images(
    ctx: click.Context, api_url: str, output_file: TextIO, api_limit: int,
):
    """List images from wikiproject (titles and URLs)."""
    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    i: int = 0
    for image in api.get_image_list(api_limit):
        title_regex = re.match(r'.+?\:(.*)', image['title'])
        if title_regex is None:
            raise ValueError()  # TODO
        title: str = title_regex.group(1)
        filename: str = get_safe_filename(title, i)
        url: str = image['url']
        click.echo(
            'FILE2\n{}\n{}\n{}'.format(
                title, url, filename
            ),
            file=output_file
        )
        i += 1


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('category', type=click.STRING)
@click.option(
    '--output-file', type=click.File('wt'),
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
def list_category_images(
    ctx: click.Context, api_url: str, category: str, output_file: TextIO,
    api_limit: int, api_image_ids_limit: int,
):
    """List images from category (titles and URLs)."""
    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
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
            url: str = image_data['url']
            click.echo(
                'FILE2\n{}\n{}\n{}'.format(
                    title, url, filename
                ),
                file=output_file
            )
            i += 1


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.option(
    '--output-file', type=click.File('wt'),
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
    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    for namespace in api.get_namespace_list():
        for page_name in api.get_page_list(
            namespace, api_limit
        ):
            click.echo(
                '{}'.format(page_name),
                file=output_file
            )


@click.command()
@click.pass_context
@click.argument('api_url', type=click.STRING)
@click.argument('namespace', type=click.INT)
@click.option(
    '--output-file', type=click.File('wt'),
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
    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    for page_name in api.get_page_list(
        namespace, api_limit
    ):
        click.echo(
            '{}'.format(page_name),
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
    ctx: click.Context, output_directory, api_url: str, all_namespaces: bool,
    file_entry_num: int, api_limit: int
):
    """List deleted revision from wikiproject in JSON format."""
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

    file_number = 0

    namespaces: Iterable[int] = [0]
    if all_namespaces:
        namespaces = api.get_namespace_list()

    for namespace in namespaces:
        chunk: List[Dict[str, Any]] = []
        for revision in api.get_deletedrevs_list(
                namespace, api_limit
        ):
            chunk.append(revision)

            if len(chunk) == file_entry_num:
                output_file_path = os.path.join(
                    output_directory, 'entry-{}.json'.format(file_number)
                )
                with open(output_file_path, 'wt') as output_file:
                    json.dump(
                        chunk,
                        output_file,
                        ensure_ascii=False
                    )

                chunk = []
                file_number += 1

    if len(chunk) > 0:
        output_file_path = os.path.join(
            output_directory, 'entry-{}.json'.format(file_number)
        )
        with open(output_file_path, 'wt') as output_file:
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
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

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
                click.echo('Deleted {}'.format(page_name))
                deleted_num += 1
            except mediawiki.CanNotDelete:
                click.echo('Can not delete {}'.format(page_name))
                failed_num += 1

    click.echo('{} pages deleted.'.format(deleted_num))
    if failed_num > 0:
        click.echo('{} pages not deleted.'.format(deleted_num))


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
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

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
            click.echo('Edited {}'.format(page_name))
            edited_num += 1

    click.echo('{} pages edited.'.format(edited_num))


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
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

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
            click.echo('Edited {}'.format(page_name))
            edited_num += 1

    click.echo('{} pages edited.'.format(edited_num))


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
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

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
def download_images(ctx: click.Context, list_file: TextIO, download_dir):
    """Download images listed in file."""
    with click.progressbar(list(read_image_list(list_file))) as bar:
        for image in bar:
            r = requests.get(image['url'], stream=True)
            if r.status_code == 200:
                image_filename = os.path.join(download_dir, image['filename'])
                with open(image_filename, 'wb') as image_file:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, image_file)
            elif r.status_code != 404:
                click.echo(
                    'Falied to download URL {} (status code: {}).'.format(
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
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

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
def upload_images(
    ctx: click.Context, list_file: TextIO, download_dir, api_url: str
):
    """Upload images listed in file."""
    if 'MEDIAWIKI_CREDENTIALS' not in ctx.obj:
        raise click.ClickException('User credentials not given')
    user_credentials: Tuple[str, str] = ctx.obj['MEDIAWIKI_CREDENTIALS']

    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)
    api.api_login(user_credentials[0], user_credentials[1])

    with click.progressbar(list(read_image_list(list_file))) as bar:
        for image in bar:
            image_name: str = image['name']
            image_filename: str = os.path.join(download_dir, image['filename'])
            with open(image_filename, 'rb') as image_file:
                try:
                    api.upload_file(
                        image_name, image_file,
                        mimetypes.guess_type(image_name)[0]
                    )
                except mediawiki.MediaWikiAPIError as exc:
                    click.echo(
                        'Falied to upload file {}: {}.'.format(
                            image_name, str(exc)
                        )
                    )


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
              type=click.DateTime(),  # type: ignore
              help='Start date for counting edits')
@click.option('--end',
              type=click.DateTime(),  # type: ignore
              help='End date for counting edits')
@click.option('--output-format', default='mediawiki',
              type=click.Choice(['txt', 'mediawiki', 'json']),
              help='Output data format')
@click.option('--redirect-regex-text',
              default=r'^Перенаправление на \[\[.+\]\]$', type=click.STRING,
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
    api = get_mediawiki_api(ctx.obj['MEDIAWIKI_VERSION'], api_url)

    regex_redirect = re.compile(redirect_regex_text)

    users = read_user_data(user_list_file)

    namespaces_raw = json.load(namespacefile)
    if not isinstance(namespaces_raw, dict):
        raise ValueError()
    namespaces_edit_weights = namespaces_raw['edit_weights']
    namespaces_edit_weights = dict(
        map(lambda key: (int(key), namespaces_edit_weights[key]),
            namespaces_edit_weights))
    namespaces_page_weights = namespaces_raw['page_weights']
    namespaces_page_weights = dict(
        map(lambda key: (int(key), namespaces_page_weights[key]),
            namespaces_page_weights))

    users_data: Dict[str, Dict[str, Any]] = {}
    for user in users:
        click.echo('Processing user {}...'.format(user))
        user_vote_power: float = 0.0
        user_new_pages: int = 0
        user_data: Dict[str, Any] = {}

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

    if format == 'txt':
        for user in users_data:
            click.echo('User {}'.format(user))
            for key in user_data:
                click.echo('{}: {}'.format(key, user_data[key]))
            click.echo('')
    elif output_format == 'json':
        click.echo(json.dumps(users_data))
    elif output_format == 'mediawiki':
        click.echo('{| class="wikitable"')
        click.echo(' ! Участник')
        for namespace in namespaces_edit_weights:
            click.echo(' ! N{}'.format(namespace))
        click.echo(' ! A')
        click.echo(' ! Сила голоса (автоматическая)')
        click.echo(' ! Сила голоса (итоговая)')
        for user in users_data:
            click.echo(' |-')
            click.echo(' | {{{{ U|{} }}}}'.format(user))
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


if __name__ == '__main__':
    # pylint: disable=unexpected-keyword-arg, no-value-for-parameter
    cli(obj={})
