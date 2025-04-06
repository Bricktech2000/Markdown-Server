import werkzeug
import flask
import time
import os

app = flask.Flask(__name__, template_folder='.')
client = 'client/'


def preprocess_markdown(source):
  def quote(string, *args, **kwargs):
    from urllib.parse import quote
    return quote(string, safe='/#', *args, **kwargs)

  def label(match):
    # below would return label `pure < function` given wikilink `[[function#pure function]]`
    # and would return label `function > slope` given wikilink `[[function#slope]]`
    match match.split('#', 1):
      case [filename]:
        return f'{filename}'
      case [filename, anchor] if anchor.endswith(filename):
        return f'{anchor.removesuffix(filename)} < {filename}'
      case [filename, anchor]:
        return f'{filename} > {anchor}'
      case _:
        assert False, 'unreachable'

  def href(match):
    # below would return href `function.md#slope` given wikilink `[[function#slope]]`
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
  from markdown import markdown

  pymdownx = ['extra', 'arithmatex', 'highlight', 'tasklist', 'tilde', 'saneheaders']
  extensions = [f'pymdownx.{ext}' for ext in pymdownx] + ['sane_lists', 'toc']  # `toc` adds `id`s to headers
  configs = {'pymdownx.arithmatex': {'generic': True}, 'toc': {'separator': ' '}}

  year = time.strftime('%Y')
  root = os.path.dirname(path).split('/')[0] or '(root)'
  base = os.path.basename(path).removesuffix('.md') or '(index)'
  content = markdown(source, extensions=extensions, extension_configs=configs, tab_length=2)
  return flask.render_template('template.html', year=year, root=root, base=base, path=path, content=content)


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
