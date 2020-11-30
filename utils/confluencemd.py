import re

from typing import List

import atlassian
import markdown2

from utils.log import logger, is_debug

CF_URL = re.compile(r'(?P<host>https?://[^/]+)/.*/(?P<page_id>\d+)/')

class ConfluenceMD(atlassian.Confluence):

    def __init__(self, url, username, token):
        super().__init__(url=url,
                username=username,
                password=token)


    def update_existing(self, md_file: str, page_id: str = None) -> None:
        logger.debug(f"Updating page `{page_id}` based on `md_file` file")
        html = ConfluenceMD.md_file_to_html(md_file)
        page_id_from_meta, host = ConfluenceMD.parse_confluence_url(html.metadata)

        if page_id == None:
            page_id = page_id_from_meta

        assert page_id, (f"Can't update page without page_id given either by "
                f"`--page_id` parameter or via `confluence-url` tag in `{md_file}` file")

        title = self.get_page_title_by_id(page_id)

        logger.debug(f"Updating page_id `{page_id}` titled `{title}`")
        self.update_page(page_id, title,
                html, parent_id=None, type='page', representation='storage',
                minor_edit=True)


    def create_page(self, md_file: str, parent_id: str, title: str,
            add_meta:bool=False) -> None:

        logger.debug(f"Creating new page `title` based on `md_file` file")
        space = self.get_page_space(parent_id)

        if self.page_exists(space, title):
            page_id = self.get_page_id(space, title)
            assert False, (f"Page titled `{title}` already exists in "
                    f"the `{space}` space. Can't create another one.")

        html = ConfluenceMD.md_file_to_html(md_file)
        page_id_from_meta, host = ConfluenceMD.parse_confluence_url(html.metadata)
        assert not page_id_from_meta, (f"Metadata pointing to an existing page "
                f"id `{page_id_from_meta}` present in the given markdown file. "
                f"Is this create or update?")
        
        response = atlassian.Confluence.create_page(self, space, title, body=html,
                parent_id=parent_id, type='page', representation='storage')

        confluence_url = ConfluenceMD.get_link_from_response(response)
        logger.debug(f"New page created {confluence_url}")

        if add_meta:
            ConfluenceMD.add_meta_to_file(md_file, confluence_url)


    @staticmethod
    def get_link_from_response(response) -> str:
        return response['_links']['base'] + response['_links']['webui']


    @staticmethod
    def add_meta_to_file(md_file: str, confluence_url: str) -> None:
        md = ConfluenceMD.get_file_contents(md_file)
        md = ("---\n"
            f"confluence-url: {confluence_url}\n"
            "---\n") + md

        with open(md_file, 'w') as f:
            f.write(md)


    def get_page_title_by_id(self, page_id: str) -> str:
        logger.debug(f"Getting page title from page id `{page_id}`")
        return self.get_page_by_id(page_id)['title']


    @staticmethod
    def get_file_contents(file: str) -> str:
        with open(file, 'r') as f:
            return f.read()


    @staticmethod
    def md_file_to_html(md_file: str) -> str:
        logger.debug("Converting MD to HTML")
        return markdown2.markdown_path(path=md_file,
                extras=['metadata', 'strike', 'tables', 'wiki-tables',
                'code-friendly', 'fenced-code-blocks', 'footnotes'])


    @staticmethod
    def parse_confluence_url(meta: str) -> List[str]:
        if 'confluence-url' not in meta:
            return (None, None)

        url = meta['confluence-url']

        logger.debug(f"Looking for host and page_id in {url} url")
        cf_url = CF_URL.search(url)
        if(cf_url):
            page_id = cf_url.group('page_id')
            host = cf_url.group('host')
            logger.debug(f"  found page_id `{page_id}` and host `{host}`")
            return (page_id, host)
        logger.debug(f"  no valid Confluence url found")
        return (None, None)
    

