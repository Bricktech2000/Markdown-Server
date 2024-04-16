# Markdown Server

_An HTTP server with Markdown-to-HTML middleware_

## Overview

This program transparently serves files from `client/` over HTTP and compiles Markdown files to HTML on-the-fly. Features include a filepath whitelist, directory indexes and a few error pages. `$\LaTeX$` syntax and `[[wikilinks]]` with `#section` anchors and `|link text` pipes are supported in Markdown files.

## Requirements

```bash
pip install flask watchdog markdown pymdown-extensions
```

## Development

```bash
flask run --debug
```

## Deployment

```bash
flask run --host=0.0.0.0 --port=80
```
