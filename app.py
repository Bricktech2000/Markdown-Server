import werkzeug
import flask
import time
import os

import mimetypes
for type_map in [
    ('text/x-c', '.c'),
    ('text/x-c', '.h'),
    ('text/x-rust', '.rs'),
    ('text/x-haskell', '.hs'),
    ('text/x-pnlc', '.pnlc'),
    ('text/x-bf', '.bf'),
    ('text/x-vim', '.vim'),
    ('text/x-c++', '.cpp'),
    ('text/x-sh', '.sh'),
    ('text/x-asm', '.s'),
    ('text/x-asm', '.asm'),
    ('text/x-forth', '.f'),
    ('text/x-bnf', '.bnf'),
    ('text/x-go', '.go'),
    ('text/x-csv', '.csv'),
    ('text/x-tsv', '.tsv'),
]:
  mimetypes.add_type(*type_map)

app = flask.Flask(__name__, template_folder='.')
client = 'client/'


def preprocess_markdown(source):
  def quote(string, *args, **kwargs):
    from urllib.parse import quote
    return quote(string, safe='/#', *args, **kwargs)

  # [[morphism]]                      ==>  morphism
  # [[function#pure function]]        ==>  pure <function
  # [[morphism#homomorphism]]         ==>  homo<morphism
  # [[matrix#matrix multiplication]]  ==>  matrix> multiplication
  # [[eigen#eigenvector]]             ==>  eigen>vector
  # [[function#slope]]                ==>  function > slope
  def label(match):
    match match.split('#', 1):
      case [filename]:
        return f'{filename}'
      case [filename, anchor] if anchor.endswith(filename):
        return f'{anchor.removesuffix(filename)}\u2039{filename}'
      case [filename, anchor] if anchor.startswith(filename):
        return f'{filename}\u203a{anchor.removeprefix(filename)}'
      case [filename, anchor]:
        return f'{filename}\xa0\u203a {anchor}'
      case _:
        assert False, 'unreachable'

  # [[notes.pdf]]       ==>  notes.pdf
  # [[function]]        ==>  function.md
  # [[function#slope]]  ==>  function.md#slope
  def href(match):
    extension = '.md' if '.' not in match else ''
    match match.split('#', 1):
      case [filename]:
        return f'{filename}{extension}'
      case [filename, anchor]:
        return f'{filename}{extension}#{anchor}'
      case _:
        assert False, 'unreachable'

  import re
  import random
  if random.random() < 0.001:  # I wonder what this does
    source = re.sub(r'(?<=[-_*\s]\w)\w*(?=\w)', lambda m: re.sub(r'(.)(.)', r'\2\1', m.group(0)), source)
  source = re.sub(r'\[\[([^\[\]]+?)\|([^\[\]]+?)\]\]', lambda m: f'[{m.group(2)}]({quote(href(m.group(1)))})', source)
  source = re.sub(r'\[\[([^\[\]]+?)\]\]', lambda m: f'[{label(m.group(1))}]({quote(href(m.group(1)))})', source)
  source = re.sub(r'\n\n>', '\n<!-- -->\n>', source)  # try to prevent consecutive blockquotes getting merged
  return source


def markdown_to_html(source, path):
  from markdown.inlinepatterns import SimpleTagInlineProcessor
  from markdown.extensions import Extension

  class AutoLiningFigures(Extension):
    def extendMarkdown(self, md):
      md.inlinePatterns.register(SimpleTagInlineProcessor(  # priority 200 so it runs even inside code blocks
          r"(((?<=[A-Z])([^\w\x02]?\d)+|(\d[^\w\x03]?)+(?=[A-Z])))", 'i'), 'auto_lining_figures', 200)

  from markdown import markdown
  import markupsafe

  pymdownx = ['extra', 'arithmatex', 'highlight', 'tasklist', 'tilde', 'saneheaders']
  extensions = [f'pymdownx.{ext}' for ext in pymdownx] + ['sane_lists', 'toc', AutoLiningFigures()]
  configs = {'pymdownx.arithmatex': {'generic': True}, 'toc': {'separator': ' '}}  # `toc` adds `id`s to headings

  year = time.strftime('%Y')
  content = markdown(source, extensions=extensions, extension_configs=configs, tab_length=2)
  parts = f'(root)/{os.path.dirname(path)}'.rstrip('/').split('/')
  breadcrumb = ''.join(f'<a href="./{"../" * -n}">{markupsafe.escape(part)}</a>/<wbr>' for n, part in
                       enumerate(parts, -len(parts) + 1)) + f'{markupsafe.escape(os.path.basename(path))}'
  return flask.render_template('template.html', year=year, content=content, breadcrumb=breadcrumb)


@app.route('/', defaults={'path': 'index.md'})
@app.route('/<path:path>')
def catch_all(path):
  from fnmatch import fnmatch
  whitelist = open('whitelist.txt', 'r').read().splitlines()
  if not any(fnmatch(path, pattern) for pattern in whitelist):
    return flask.abort(403)

  from contextlib import suppress
  if path.endswith('.md'):
    with suppress(FileNotFoundError):
      with open(os.path.join(client, path), 'r') as f:
        return markdown_to_html(preprocess_markdown(f.read()), path)

  if path.endswith('/'):
    with suppress(StopIteration):
      (_, dirs, files) = next(os.walk(os.path.join(client, path)))
      items = [f'- [{d}/]({d}/)' for d in dirs] + [f'- [{f}]({f})' for f in files]
      return markdown_to_html(preprocess_markdown('# Index\n' + '\n'.join(items)), path)

  return flask.send_from_directory(client, path)


@app.errorhandler(werkzeug.exceptions.HTTPException)
def http_exception_handler(e):
  path = flask.request.path.removeprefix('/')
  with open(f'{e.code}.md', 'r') as f:
    return markdown_to_html(preprocess_markdown(f.read()), path), e.code
