import os

from bs4 import BeautifulSoup
from mdict_query import mdict_query

# Get the current project directory
project_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the static directory
static_dir = os.path.join(project_dir, "static")

# Construct the path to the dictionary file
dictionary_file = os.path.join(static_dir, "MerriamWebsterV3.mdx")

# Create the IndexBuilder instance
builder = mdict_query.IndexBuilder(dictionary_file)


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    return text


def query_text_from_mdx(keyword):
    html = builder.mdx_lookup(keyword, ignorecase=True)
    return html_to_text("\n".join(html)) if html else ""


if __name__ == "__main__":
    print(query_text_from_mdx("vigorous"))
