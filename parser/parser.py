from itertools import tee, zip_longest, islice
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests import get as request_get

PEPS_API = 'https://peps.python.org/api/peps.json'


def fetch_json(url: str):
    r = request_get(url)
    r.raise_for_status()
    return r.json()


def fetch_text(url: str):
    r = request_get(url)
    r.raise_for_status()
    return r.text


def pep_parser():
    peps = fetch_json(url=PEPS_API)
    for inx, pep in peps.items():
        title = pep.get('title', 'Unknown')
        tags = [t.lower() for t in title.split() if len(t) > 3]
        page_url = pep.get('url', None)
        status = pep.get('status')
        python_version = pep.get('python_version')

        if (
            status in ['Rejected', 'Withdrawn']
            or python_version is None
            or '3.' not in python_version
        ):
            continue

        if page_url is None:
            raise ValueError('No <page_url> found')

        pep_content = fetch_text(url=page_url)
        soup = BeautifulSoup(pep_content, 'html.parser')
        pep_page_section = soup.find(id='pep-page-section')

        if not pep_page_section:
            raise ValueError('No <pep_page_section> found')

        article = pep_page_section.find('article')
        sections = article.find_all('section')

        for section in sections:
            section_id = section['id']
            link_tag = section.find('a', class_='toc-backref')
            href = link_tag['href'] if link_tag and link_tag.has_attr('href') else ''

            blocks = (
                b
                for b in section.find_all(recursive=False)
                if b.name
                not in ['h1', 'h2', 'h3', 'h4', 'section', 'details', 'img', 'hr']
            )

            current_iter, next_iter = tee(blocks)
            next_iter = islice(next_iter, 1, None)

            prev_text = None

            for current_block, next_block in zip_longest(current_iter, next_iter):
                current_text = current_block.text.strip().replace('\n', ' ')
                next_text = (
                    next_block.text.strip().replace('\n', ' ') if next_block else None
                )

                section_url = page_url + href

                parsed_url = urlparse(section_url)
                breadcrumbs = parsed_url.path.split('/')[1:-1] + [parsed_url.fragment]

                row = {
                    'page_title': title,
                    'status': status,
                    'section_title': section_id,
                    'page_url': page_url,
                    'section_url': section_url,
                    'breadcrumbs': breadcrumbs,
                    'chunk_text': current_text,
                    'prev_section_text': prev_text,
                    'next_section_text': next_text,
                    'tags': tags,
                }
                prev_text = current_text

                yield row
