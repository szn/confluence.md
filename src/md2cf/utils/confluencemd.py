import re

from typing import List

import atlassian
import markdown2

from .log import logger

CF_URL = re.compile(r'(?P<host>https?://[^/]+)/.*/(?P<page_id>\d+)')

class ConfluenceMD(atlassian.Confluence):
    def __init__(self, username:str, token:str, md_file:str, url:str = None,
            add_meta:bool=False, add_info_panel:bool=False, add_label:str=None) -> None:
        self.username = username
        self.token = token
        self.md_file = md_file
        self.url = url
        self.add_meta = add_meta
        self.add_info_panel = add_info_panel
        self.add_label = add_label

        if url:
            self.init()

    def init(self):
        super().__init__(url=self.url, username=self.username, password=self.token)

    def update_existing(self, page_id: str = None) -> None:
        logger.debug(f"Updating page `{page_id}` based on `md_file` file")
        html, page_id_from_meta, url = self.md_file_to_html()

        if page_id == None:
            logger.debug(f"Using `page_id` from `{self.md_file}` file")
            page_id = page_id_from_meta

        assert page_id, (f"Can't update page without page_id given either by "
                f"`--page_id` parameter or via `confluence-url` tag in `{self.md_file}` file")

        if self.url == None:
            logger.debug(f"Using URL ({url}) from `{self.md_file}` file")
            self.url = url
            assert self.url, (f"Can't update page without url given either by "
                    f"`--url` parameter or via `confluence-url` tag in `{self.md_file}` file`")
            self.init()

        title = self.get_page_title_by_id(page_id)

        logger.debug(f"Updating page_id `{page_id}` titled `{title}`")
        response = self.update_page(page_id, title,
                html, parent_id=None, type='page', representation='storage',
                minor_edit=True)

        if self.add_meta:
            confluence_url = ConfluenceMD.get_link_from_response(response)
            self.add_meta_to_file(confluence_url)
        
        if self.add_label:
            self.add_label_to_page(page_id)


    def create_page(self, parent_id: str, title: str, overwrite: bool) -> None:
        assert title, "Provide a title for a newly created page"
        assert parent_id, "Provide parent_id for a newly created page"
        space = self.get_page_space(parent_id)

        page_id = None
        if self.page_exists(space, title):
            page_id = self.get_page_id(space, title)
            assert overwrite, (f"Page titled `{title}` already exists in "
                    f"the `{space}` space. Use --overwrite to force it.")

        html, page_id_from_meta, url = self.md_file_to_html()
        assert not page_id_from_meta and overwrite, (f"Metadata pointing to an existing page "
                f"id `{page_id_from_meta}` present in the given markdown file. "
                f"Use --overwrite to force it.")
        
        overwrite = page_id or page_id_from_meta

        if overwrite:
            logger.debug(f"Overwriting existing page `{title}` based on `{self.md_file}` file")
            response = self.update_page(page_id or page_id_from_meta, title,
                    html, parent_id=None, type='page', representation='storage',
                    minor_edit=True)
        else:
            logger.debug(f"Creating new page `{title}` based on `{self.md_file}` file")
            response = atlassian.Confluence.create_page(self, space, title, body=html,
                    parent_id=parent_id, type='page', representation='storage', editor="v2")

        confluence_url = ConfluenceMD.get_link_from_response(response)
        logger.debug(f"{'Page overwritten' if overwrite else 'New page created'} {confluence_url}")

        self.add_meta_to_file(confluence_url)
        
        page_id = ConfluenceMD.get_page_id_from_response(response)
        self.add_label_to_page(page_id)


    @staticmethod
    def get_link_from_response(response) -> str:
        return response['_links']['base'] + response['_links']['webui']


    @staticmethod
    def get_page_id_from_response(response) -> str:
        return response['id']


    def add_meta_to_file(self, confluence_url: str) -> None:
        if not self.add_meta:
            return

        md = ConfluenceMD.get_file_contents(self.md_file)
        md = ("---\n"
            f"confluence-url: {confluence_url}\n"
            "---\n") + md

        with open(self.md_file, 'w') as f:
            f.write(md)


    def get_page_title_by_id(self, page_id: str) -> str:
        logger.debug(f"Getting page title from page id `{page_id}`")
        return self.get_page_by_id(page_id)['title']


    @staticmethod
    def get_file_contents(file: str) -> str:
        with open(file, 'r') as f:
            return f.read()


    def md_file_to_html(self) -> str:
        logger.debug("Converting MD to HTML")
        html = markdown2.markdown_path(path=self.md_file,
                extras=['metadata', 'strike', 'tables', 'wiki-tables',
                'code-friendly', 'fenced-code-blocks', 'footnotes'])

        page_id_from_meta, url = ConfluenceMD.parse_confluence_url(html.metadata)
        if self.add_info_panel:
            html = self.get_info_panel() + html
        return html, page_id_from_meta, url


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

    def add_label_to_page(self, page_id:str) -> None:
        if not self.add_label:
            return
        self.set_page_label(page_id, self.add_label)

    def get_info_panel(self):
        return (f'''<p><strong>Automatic content</strong> This page was generated automatically from <code>{self.md_file}</code> file.
        Do not edit it on Confluence.</p><hr />
        ''')
