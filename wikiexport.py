# -*- coding: utf-8 -*-
"""MediaWiki script for exporting data and downloading images."""
from typing import List, Iterator, Dict, Any, IO
import os
import shutil

import click
import requests


class MediaWikiAPIError(Exception):
    """MediaWiki API error."""

    pass


def get_namespace_list(api_url: str) -> List[int]:
    """Iterate over namespaces in wiki."""
    params: Dict[str, Any] = {
        'action': 'query',
        'meta': 'siteinfo',
        'siprop': 'namespaces',
        'format': 'json',
    }

    r = requests.get(api_url, params=params)
    if r.status_code != 200:
        raise MediaWikiAPIError(None)

    data = r.json()
    if 'error' in data:
        raise MediaWikiAPIError(data['error'])
    namespaces = data['query']['namespaces']

    return list(
        filter(
            lambda namespace_id: namespace_id >= 0,
            map(
                lambda namespace: int(namespace),
                namespaces.keys()
            )
        )
    )


def get_image_list(api_url: str, limit: int) -> Iterator[Dict[str, str]]:
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
        r = requests.get(api_url, params=current_params)
        if r.status_code != 200:
            raise MediaWikiAPIError(None)

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


def get_page_list(api_url: str, namespace: int, limit: int) -> Iterator[str]:
    """Iterate over all page names in wiki."""
    params: Dict[str, Any] = {
        'action': 'query',
        'list': 'allpages',
        'apnamespace': namespace,
        'apdir': 'ascending',
        'aplimit': limit,
        'format': 'json',
    }
    last_continue: Dict[str, Any] = {}

    while True:
        current_params = params.copy()
        current_params.update(last_continue)
        r = requests.get(api_url, params=current_params)
        if r.status_code != 200:
            raise MediaWikiAPIError(None)

        data = r.json()
        if 'error' in data:
            raise MediaWikiAPIError(data['error'])
        pages = data['query']['allpages']

        for image_data in pages:
            yield image_data['title']

        if 'query-continue' not in data:
            break
        last_continue = data['query-continue']['allpages']


def read_image_list(image_list_file: IO) -> Iterator[Dict[str, str]]:
    """
    Iterate over image data listed in file `image_list_file`.

    Each image data is dictionary with two fields: `name` and `url`.
    """
    file_iterator = iter(image_list_file)
    try:
        while True:
            next(file_iterator)
            title_line = next(file_iterator)
            url_line = next(file_iterator)
            yield {
                'name': title_line.strip()[5:],
                'url': url_line.strip(),
            }
    except StopIteration:
        pass


@click.group()
def cli():
    """Run MediaWiki script for exporting data and downloading images."""
    pass


@click.command()
@click.argument('api_url', type=str)
@click.option(
    '--output-file', type=click.File('wt'),
    help='Text file to write image list'
)
@click.option(
    '--api-limit', default=500, type=int,
    help='Maximum number of entries per API request'
)
def list_images(api_url: str, output_file: IO, api_limit: int):
    """List images from wikiproject (titles and URLs)."""
    for image in get_image_list(api_url, api_limit):
        click.echo(
            'FILE\n{}\n{}'.format(image['title'], image['url']),
            file=output_file
        )


@click.command()
@click.argument('api_url', type=str)
@click.option(
    '--output-file', type=click.File('wt'),
    help='Text file to write page list'
)
@click.option(
    '--api-limit', default=500, type=int,
    help='Maximum number of entries per API request'
)
def list_pages(api_url: str, output_file: IO, api_limit: int):
    """List page names from wikiproject."""
    for namespace in get_namespace_list(api_url):
        for page_name in get_page_list(api_url, namespace, api_limit):
            click.echo(
                '{}'.format(page_name),
                file=output_file
            )


@click.command()
@click.argument('list_file', type=click.File('rt'))
@click.argument(
    'download_dir', type=click.Path(file_okay=False, dir_okay=True)
)
def download_images(list_file, download_dir):
    """Download images listed in file."""
    with click.progressbar(list(read_image_list(list_file))) as bar:
        for image in bar:
            r = requests.get(image['url'], stream=True)
            if r.status_code == 200:
                image_filename = os.path.join(download_dir, image['name'])
                with open(image_filename, 'wb') as image_file:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, image_file)
            elif r.status_code != 404:
                click.echo(
                    'Falied to download URL {} (status code: {}).'.format(
                        r.url, r.status_code
                    )
                )


cli.add_command(list_images)
cli.add_command(list_pages)
cli.add_command(download_images)


if __name__ == '__main__':
    cli()
