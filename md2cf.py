#!/usr/bin/env python3
import os
import sys
import argparse
from argparse import RawTextHelpFormatter

from atlassian.errors import ApiError

from utils.log import logger, init_logger, headline
from utils.confluencemd import ConfluenceMD

ACTIONS = {}

def register_action(function):
    ACTIONS[function.__name__] = function.__doc__
    def wrapper(args):
        headline(function.__doc__)
        function(args)
        headline("End {}".format(function.__name__), True)
    return wrapper

def init_confluence(args):
    return ConfluenceMD(args.url, args.user, args.token)

@register_action
def update(args) -> int:
    """Updates page content based on given page_id or medata in Markdown file"""
    confluence = init_confluence(args)
    confluence.update_existing(args.file.name, args.page_id)

@register_action
def create(args):
    """Creates new page under given parent id"""
    confluence = init_confluence(args)
    confluence.create_page(args.file.name, args.parent_id, args.title,
            args.add_meta)

def main():
    actions = list(ACTIONS.keys())

    description = """Markdown to Confluence

Example workfloe:

1 Create a new page under --parent_id:
  $ ./md2cf.py --user user@name.net --token 9a8dsadsh --url https://your-domain.atlassian.net \\
          create --file markdown.md --parent_id 18237182 --title "new title" --add_meta

2 The page is created and the file is decorated with medatada:
  $ head -n 3 markdown.md
  ---
  confluence-url: https://your-domain.atlassian.net/wiki/spaces/SP/pages/18237182/new+title
  ---

3 Performing an update does not require providing --page_id:
  $ ./md2cf.py --user user@name.net --token 9a8dsadsh --url https://your-domain.atlassian.net \\
          update --file markdown.md

4 Doing an update with --page_id is still possible:
  $ ./md2cf.py --user user@name.net --token 9a8dsadsh --url https://your-domain.atlassian.net \\
          update --file markdown.md --page_id 17006931

To create Atlassian API Token go to:
  https://id.atlassian.com/manage-profile/security/api-tokens

Actions:
"""
    
    for action in actions:
        description += f"  {action:10}\t\t{ACTIONS[action]}\n"

    parser = argparse.ArgumentParser(add_help=True,
            prog="./md2cf.py",
            formatter_class=RawTextHelpFormatter,
            description=description)

    auth_args = parser.add_argument_group('required auth parameters')
    auth_args.add_argument("-u", "--user", action="store", required=True,
            help="Atlassian username/email")
    auth_args.add_argument("-t", "--token", action="store", required=True,
            help="Atlassian API token")
    auth_args.add_argument("-l", "--url", action="store", required=True,
            help="Atlassian instance URL")

    create_args = parser.add_argument_group('create page parameters')
    create_args.add_argument("--parent_id", action="store",
            help="define parent page id while creating a new page")
    create_args.add_argument("--title", action="store",
            help="define page title while creating a new page")
    create_args.add_argument("--add_meta", action="store_true",
            help="adds metadata to .md file for easy editing")

    update_args = parser.add_argument_group('update page arguments')
    update_args.add_argument("--page_id", action="store",
            help="define (or override) page id while updating a page")

    parser.add_argument("--file", action="store",
            type=argparse.FileType('r'), required=True,
            help="input markdown file to process")

    parser.add_argument("-v", "--verbose", action="store_true",
            help="verbose mode")
    parser.add_argument("action", help="Action to run", choices=ACTIONS)

    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    init_logger(args)

    try:
        globals()[args.action](args)
    except (RuntimeError, AssertionError, Exception) as e:
        logger.error(e)
        quit(-1)


if __name__ == "__main__":
    main()

