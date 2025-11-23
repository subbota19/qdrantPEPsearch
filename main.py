from qdrant_client import models

from parser.parser import pep_parser
from search.search import PEPSearchEngine


def main():
    pep_search_engine = PEPSearchEngine()
    pep_search_engine.create_collection(recreate=True)

    pep_search_engine.create_index(
        field_name='status', field_schema=models.PayloadSchemaType.KEYWORD
    )

    pep_search_engine.create_index(
        field_name='page_url', field_schema=models.PayloadSchemaType.KEYWORD
    )

    pep_search_engine.upload_stream_documents(documents_iter=pep_parser())

    query = 'building time in JIT compilation'

    results = pep_search_engine.search(
        query=query,
        search_filter=pep_search_engine.build_filter(
            [{'field': 'status', 'op': 'in', 'value': ['Accepted', 'Final']}]
        ),
    )

    pep_search_engine.visualize_results(
        results=results,
        query=query,
        snippet_size=400,
    )


if __name__ == '__main__':
    main()
