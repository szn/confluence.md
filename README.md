# confluence.md

Push markdown files straight to a Confluence page.

## What it does?

`confluence.md` allows you to push any markdown file to Confluence. You can create
a new page (under given parent) or update an existing one.

## How to install?

It's as easy as:

```
$ pip install confluence.md
```

## How to use it?

Markdown to Confluence

Example workflow:

### 1. Create a new page under `--parent_id`:
```
$ confluence.md --user user@name.net --token 9a8dsadsh --url https://your-domain.atlassian.net \
        create --file README.md --parent_id 182371 --title "new title" --add_meta
```

### 2. The page is created and the file is decorated with metadata:
```
$ head -n 3 markdown.md
---
confluence-url: https://your-domain.atlassian.net/wiki/spaces/SP/pages/18237182/new+title
---
```

### 3. Performing an update does not require providing `--page_id` and `--url`:
```
$ confluence.md --user user@name.net --token 9a8dsadsh update --file README.md
```

Doing an update with `--page_id` and `--url` is still possible.

Consider adding useful `--add_info` option.

To create Atlassian API Token go to [api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

**Actions:**

- `update`    		Updates page content based on given `page_id` or metadata in Markdown file
- `create`    		Creates new page under given `parent_id`

**positional arguments:**

- `{update,create}`         Action to run

**optional arguments:**

- `-h`, `--help`            show this help message and exit
- `--file FILE`             input markdown file to process
- `--add_meta`              adds metadata to .md file for easy editing
- `--add_info`              adds info panel **automatic content** do not edit on top of the page
- `--add_label` `ADD_LABEL` adds label to page
- `-v`, `--verbose`         verbose mode
- `-q`, `--quiet`           quiet mode

**required auth parameters:**

- `-u` `USER`, `--user` `USER`    Atlassian username/email
- `-t` `TOKEN`, `--token` `TOKEN` Atlassian API token
- `-l` `URL`, `--url` `URL`       Atlassian instance URL

**create page parameters:**

- `--parent_id` `PARENT_ID` define parent page id while creating a new page
- `--title` `TITLE`         define page title while creating a new page
- `--overwrite`             force overwrite if page with this title already exists

**update page arguments:**

-  `--page_id` `PAGE_ID`     define (or override) page id while updating a page