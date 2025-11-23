import os
from re import findall
from typing import List, Dict, Any, Iterable

from colorama import Fore, Style
from dotenv import load_dotenv
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
from qdrant_client import QdrantClient, models
from qdrant_client.conversions import common_types as types

DENSE_MODEL_ID = 'BAAI/bge-base-en-v1.5'
SPARSE_MODEL_ID = 'prithivida/Splade_PP_en_v1'
COLBERT_MODEL_ID = 'colbert-ir/colbertv2.0'


class PEPSearchEngine:
    def __init__(
        self,
        collection_name: str = 'pep_search',
        dense_model_id: str = DENSE_MODEL_ID,
        sparse_model_id: str = SPARSE_MODEL_ID,
        colbert_model_id: str = COLBERT_MODEL_ID,
        dense_dim: int = 768,
        colbert_dim: int = 128,
    ):
        """Initialize embeddings, Qdrant client, and configs."""

        load_dotenv()
        self.collection_name = collection_name
        self.dense_dim = dense_dim
        self.colbert_dim = colbert_dim

        self.dense_model = TextEmbedding(dense_model_id)
        self.sparse_model = SparseTextEmbedding(sparse_model_id)
        self.colbert_model = LateInteractionTextEmbedding(colbert_model_id)

        self.client = QdrantClient(
            url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY')
        )

    def create_index(self, field_name: str, field_schema: types.PayloadSchemaType):
        """Create an index for a payload field if it does not exist."""

        info = self.client.get_collection(self.collection_name)

        if field_name not in info.payload_schema:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )

    @staticmethod
    def visualize_results(
        results: Iterable[Dict[str, str]], query: str, snippet_size: int = 200
    ):
        """Pretty-print results with highlighted query tokens."""

        if not results:
            print('No results.')
            return

        tokens = [t.lower() for t in findall(r'\w+', query)]

        print('\n' + '=' * 80)
        print(f'Query: {query}')
        print('=' * 80 + '\n')

        for i, r in enumerate(results, start=1):
            snippet = r.get('chunk_text', '')[:snippet_size]

            for token in tokens:
                snippet = (
                    snippet.replace(token, f'{Fore.GREEN}{token}{Style.RESET_ALL}')
                    .replace(
                        token.upper(), f'{Fore.GREEN}{token.upper()}{Style.RESET_ALL}'
                    )
                    .replace(
                        token.title(), f'{Fore.GREEN}{token.title()}{Style.RESET_ALL}'
                    )
                )

            print(f"#{i} — score={r['score']:.4f}")
            print(f"PEP: {r['page_title']}")
            print(f"Section: {r.get('section', '(none)')}")
            print(f"URL: {r['section_url']}")
            print(f'Snippet: {snippet}')
            print('-' * 80)

    @staticmethod
    def build_filter(conditions: list[dict]) -> models.Filter | None:
        """Build a Qdrant filter from simple declarative conditions."""

        qdrant_conditions = []

        for cond in conditions:
            field = cond.get('field')
            op = cond.get('op')
            value = cond.get('value')

            if op == '==':
                qdrant_conditions.append(
                    models.FieldCondition(key=field, match=models.MatchValue(value=value))
                )

            elif op == 'in':
                qdrant_conditions.append(
                    models.FieldCondition(key=field, match=models.MatchAny(any=value))
                )

            elif op in ('>=', '>'):
                qdrant_conditions.append(
                    models.FieldCondition(key=field, range=models.Range(gte=value))
                )

            elif op in ('<=', '<'):
                qdrant_conditions.append(
                    models.FieldCondition(key=field, range=models.Range(lte=value))
                )

            elif op == 'range':
                g, l = value
                qdrant_conditions.append(
                    models.FieldCondition(key=field, range=models.Range(gte=g, lte=l))
                )

            else:
                raise ValueError(f'Unsupported filter operation: {op}')

        return models.Filter(must=qdrant_conditions) if qdrant_conditions else None

    def create_collection(self, recreate: bool = True) -> None:
        """Create (or recreate) Qdrant collection."""

        if recreate and self.client.collection_exists(self.collection_name):
            self.client.delete_collection(collection_name=self.collection_name)

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    'dense': models.VectorParams(
                        size=self.dense_dim,
                        distance=models.Distance.COSINE,
                    ),
                    'colbert': models.VectorParams(
                        size=self.colbert_dim,
                        distance=models.Distance.COSINE,
                        multivector_config=models.MultiVectorConfig(
                            comparator=models.MultiVectorComparator.MAX_SIM
                        ),
                        hnsw_config=models.HnswConfigDiff(m=0),
                    ),
                },
                sparse_vectors_config={'sparse': models.SparseVectorParams()},
            )

    def upload_stream_documents(
        self, documents_iter: Iterable[Dict], parallel: int = 0, batch_size: int = 256
    ) -> None:
        """Stream chunked documents into Qdrant."""
        batch = []
        point_id = 0
        for row in documents_iter:
            text = row.get('chunk_text')

            dense_vec = next(self.dense_model.embed([text], parallel=parallel))
            sparse_emb = next(self.sparse_model.embed([text], parallel=parallel))
            colbert_vec = next(self.colbert_model.embed([text], parallel=parallel))

            point = models.PointStruct(
                id=point_id,
                vector={
                    'dense': dense_vec,
                    'sparse': sparse_emb.as_object(),
                    'colbert': colbert_vec,
                },
                payload=row,
            )
            batch.append(point)
            point_id += 1

            if len(batch) >= batch_size:
                self.client.upload_points(
                    collection_name=self.collection_name, points=batch
                )
                batch.clear()

        if batch:
            self.client.upload_points(collection_name=self.collection_name, points=batch)

    def search(
        self,
        query: str,
        search_filter: models.Filter | None = None,
        dense_limit: int = 100,
        sparse_limit: int = 100,
        rff_limit: int = 100,
        colbert_top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Hybrid RRF + ColBERT rerank."""
        dense_q = next(self.dense_model.query_embed(query))
        sparse_q = next(self.sparse_model.query_embed(query)).as_object()
        colbert_q = next(self.colbert_model.query_embed(query))

        # Stage 1 — hybrid RRF
        hybrid_prefetch = models.Prefetch(
            prefetch=[
                models.Prefetch(
                    query=dense_q,
                    using='dense',
                    filter=search_filter,
                    limit=dense_limit,
                ),
                models.Prefetch(
                    query=sparse_q,
                    using='sparse',
                    filter=search_filter,
                    limit=sparse_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=rff_limit,
        )

        # Stage 2 — rerank with ColBERT
        result = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=hybrid_prefetch,
            query=colbert_q,
            using='colbert',
            limit=colbert_top_k,
        )

        formatted = []

        for p in result.points:
            formatted.append(
                {
                    'score': p.score,
                    'page_title': p.payload.get('page_title'),
                    'section_url': p.payload.get('section_url'),
                    'section_title': p.payload.get('section_title'),
                    'chunk_text': p.payload.get('chunk_text'),
                    'breadcrumbs': p.payload.get('breadcrumbs'),
                }
            )

        return formatted
