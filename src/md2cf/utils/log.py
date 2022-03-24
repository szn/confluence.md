import logging

import coloredlogs
from termcolor import colored

logger = logging.getLogger("net.dirtyagile.confluence.md")


def init_logger(args):
    coloredlogs.install(
            level='WARN' if args.quiet else ('DEBUG' if args.verbose else 'INFO'),
            logger=logger,
            fmt='%(asctime)s %(programname)s %(message)s',
            programname='>',
            datefmt='%H:%m:%S',
            field_styles= {
                    'asctime': {'color': 'black', 'bright': True},
                    'hostname': {'color': 'magenta'},
                    'levelname': {'bold': True, 'color': 'black'},
                    'name': {'color': 'blue'},
                    'programname': {'color': 'black', 'bright': True},
                    'username': {'color': 'yellow'}},
            level_styles= {
                    'critical': {'bold': True, 'color': 'red'},
                    'debug': {'color': 'white', 'faint': True},
                    'error': {'color': 'red'},
                    'info': {'color': 'white', 'faint': False},
                    'notice': {'color': 'magenta'},
                    'warning': {'color': 'yellow'}})

    logging.getLogger("net.dirtyagile.confluence.md").level = logging.WARN if args.quiet else (logging.DEBUG if args.verbose else logging.INFO)


def is_debug():
    return logger.level <= logging.DEBUG


def headline(msg, end=False):
    logger.info(colored(" {:80}".format(msg), 'blue',
            attrs=['reverse']))

