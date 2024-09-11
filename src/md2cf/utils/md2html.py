"""
Converts markdown to html
"""
import re
import os
from typing import Any, List, Tuple, Optional, Dict
import markdown2

from .log import logger

CF_URL = re.compile(r"(?P<host>https?://[^/]+)/.*/(?P<page_id>\d+)")
IMAGE_PATTERN = re.compile(r"\!\[(?P<alt>.*)\]\((?P<path>[^:)]+)\)")


def md_to_html(md_file: str,
               add_info_panel: bool) -> Tuple[Any, Optional[str], Optional[str], List]:
    """Converts given md_file to html"""

    logger.debug("Converting MD to HTML")
    md = __get_file_contents(md_file)
    images = __get_images_from_file(md)

    html = markdown2.markdown_path(
        path=md_file,
        extras=[
            "metadata",
            "strike",
            "tables",
            "wiki-tables",
            "code-friendly",
            "fenced-code-blocks",
            "footnotes",
        ],
    )
    page_id_from_meta, url = __parse_confluence_url(html.metadata)
    if add_info_panel:
        html = __get_info_panel(md_file) + html

    md_file_dir = os.path.dirname(md_file)
    html = __rewrite_images(html, md_file_dir, images)
    html = __fix_code_blocks(html)
    return html, page_id_from_meta, url, images

def __parse_confluence_url(meta: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Parses Confluence page URL and returns page_id and host"""
    if "confluence-url" not in meta:
        return (None, None)

    url = meta["confluence-url"]

    logger.debug("Looking for host and page_id in %s url", url)
    cf_url = CF_URL.search(url)
    if cf_url:
        page_id = cf_url.group("page_id")
        host = cf_url.group("host")
        logger.debug("  found page_id `%s` and host `%s`", page_id, host)
        return (page_id, host)
    logger.debug("  no valid Confluence url found")
    return (None, None)

def __get_info_panel(md_file: str) -> str:
    """
    Returns str with html info page to be placed on a Confluence page
    if --add_info is added
    """
    return f"""
    <p><strong>Automatic content</strong> - Do not edit this page in Confluence.
    Page automatically generated from: <code>{md_file}</code></p><hr />
    """

def __get_images_from_file(md: str) -> List:
    logger.debug("Getting list of images from MD file")
    images = []
    for image in IMAGE_PATTERN.finditer(md):
        path = image.group("path")
        images.append((image.group("alt"), path))
        logger.debug("  - found image %s", path)
    return images

def __rewrite_images(html: str,
                     md_file_dir: str,
                     images: List[Tuple[str, str]]
                     ) -> str:
    """Replaces <img> html tags with Confluence specific <ac:image> and uploads
        images as attachments"""
    for (alt, path) in images:
        rel_path = os.path.join(md_file_dir, path)
        if not os.path.isfile(rel_path):
            assert os.path.isfile(path), f"File `{path}` does not exist"
            logger.debug("File `%s` does not exist, using file relative to "
                            "current dir `%s`", rel_path, path)
            rel_path = path

        old = f'<img src="{path}" alt="{alt}" />'
        new = f'<ac:image> <ri:attachment ri:filename="{os.path.basename(rel_path)}" />' \
                '</ac:image>'
        if html.find(old) != -1:
            logger.debug("replace image tag `%s` with `%s`", old, new)
            html = html.replace(old, new)
        else:
            logger.warning("image tag `%s` not found in html", old)
    return html

def __fix_code_blocks(html: str) -> str:
    """
    @TODO temporary fix for https://github.com/szn/confluence.md/issues/12
    """
    html = html.replace('<pre><code>', '<code>')
    return html.replace("</code></pre>", "</code>")

def __get_file_contents(file: str) -> str:
    """Return file contents"""
    with open(file, "r", encoding="utf-8") as stream:
        return stream.read()
