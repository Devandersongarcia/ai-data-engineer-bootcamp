"""
Fast execution script for the RAG ingestion pipeline.
Uses simplified chunking to avoid timeouts.
"""

import asyncio
import time
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from typing import Any

from config import load_settings
from data_loader import MinIODocumentLoader
from preprocessors import DocumentPreprocessor
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from vector_stores import DualVectorStoreManager
from chunking_strategies import Chunk, ChunkType
import numpy as np
import hashlib


async def run_fast_pipeline() -> dict[str, Any]:
    """Run optimized pipeline with simple chunking.
    
    Returns:
        Pipeline execution results
    """
    
    logger.info("Starting optimized RAG pipeline...")
    start_time = time.time()
    
    # Load settings
    settings = load_settings()
    
    # Initialize components
    logger.info("Initializing components...")
    loader = MinIODocumentLoader(settings)
    preprocessor = DocumentPreprocessor()
    vector_manager = DualVectorStoreManager(settings)
    
    # Initialize embedding model with optimized batch size
    embedding_model = OpenAIEmbedding(
        api_key=settings.openai.api_key,
        model="text-embedding-3-large",
        embed_batch_size=20
    )
    
    # Display header  
    header = "=" * 60
    print(f"\n{header}")
    print("🚀 RAG Fast Pipeline - Optimized Processing")
    print(header)
    
    # List and load documents
    files = loader.list_docx_files()
    logger.info(f"Found {len(files)} documents in MinIO")
    
    total_chunks = 0
    successful_docs = 0
    
    for file_info in files:
        try:
            doc_start = time.time()
            logger.info(f"\n📄 Processing: {file_info['name']}")
            
            # Load document
            docs = loader.load_specific_document(file_info['name'])
            
            if not docs:
                logger.warning(f"No content found in {file_info['name']}")
                continue
            
            doc = docs[0]
            logger.info(f"  ✓ Loaded: {len(doc.text)} characters")
            
            # Preprocess
            processed_doc = preprocessor.preprocess_document(doc)
            reduction = processed_doc.metadata['preprocessing']['reduction_percentage']
            logger.info(f"  ✓ Preprocessed: {reduction}% reduction")
            
            # Create chunks with optimal parameters
            parser = SimpleNodeParser.from_defaults(
                chunk_size=512,
                chunk_overlap=50
            )
            
            nodes = parser.get_nodes_from_documents([processed_doc])
            logger.info(f"  ✓ Created {len(nodes)} chunks")
            
            # Convert to Chunk format
            chunks = []
            for i, node in enumerate(nodes):
                chunk = Chunk(
                    id=hashlib.md5(f"{file_info['name']}_{i}_{node.text[:50]}".encode()).hexdigest(),
                    text=node.text,
                    chunk_type=ChunkType.PARAGRAPH,
                    metadata={
                        **node.metadata,
                        'chunk_index': i,
                        'source_file': file_info['name'],
                        'chunk_size': len(node.text)
                    }
                )
                chunks.append(chunk)
            
            # Generate embeddings in parallel batches
            logger.info(f"  ⚡ Generating embeddings...")
            embed_start = time.time()
            
            batch_size = 20
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                texts = [c.text for c in batch]
                
                try:
                    embeddings = embedding_model.get_text_embedding_batch(texts)
                    for chunk, embedding in zip(batch, embeddings):
                        chunk.embedding = np.array(embedding)
                except Exception as e:
                    logger.error(f"  Embedding batch failed: {e}")
                    continue
            
            embed_time = time.time() - embed_start
            logger.info(f"  ✓ Embeddings generated in {embed_time:.1f}s")
            
            # Filter valid chunks
            valid_chunks = [c for c in chunks if c.embedding is not None]
            
            if valid_chunks:
                # Ingest to vector stores
                logger.info(f"  📤 Ingesting to vector stores...")
                ingest_start = time.time()
                
                results = await vector_manager.ingest_chunks(valid_chunks, strategy="both")
                
                pc_success = results.get('pinecone', {}).get('successful', 0)
                qd_success = results.get('qdrant', {}).get('successful', 0)
                
                ingest_time = time.time() - ingest_start
                logger.info(f"  ✓ Ingested in {ingest_time:.1f}s - Pinecone: {pc_success}, Qdrant: {qd_success}")
                
                total_chunks += len(valid_chunks)
                successful_docs += 1
            
            doc_time = time.time() - doc_start
            logger.info(f"  ✅ Document completed in {doc_time:.1f}s")
            
        except Exception as e:
            logger.error(f"Failed to process {file_info['name']}: {e}")
            continue
    
    # Display summary
    total_time = time.time() - start_time
    
    summary_header = "=" * 60
    print(f"\n{summary_header}")
    print("✨ Pipeline Complete!")
    print(summary_header)
    print(f"📊 Statistics:")
    print(f"  • Documents processed: {successful_docs}/{len(files)}")
    print(f"  • Total chunks: {total_chunks}")
    print(f"  • Total time: {total_time:.1f}s")
    print(f"  • Avg per document: {total_time/len(files):.1f}s")
    
    # Get final statistics
    stats = vector_manager.get_statistics()
    
    if 'pinecone' in stats:
        pc_stats = stats['pinecone']
        print(f"\n📍 Pinecone:")
        print(f"  • Total ingested: {pc_stats.get('total_ingested', 0)}")
        print(f"  • Index fullness: {pc_stats.get('index_fullness', 0):.1%}")
    
    if 'qdrant' in stats:
        qd_stats = stats['qdrant']
        print(f"\n🎯 Qdrant:")
        print(f"  • Total ingested: {qd_stats.get('total_ingested', 0)}")
        print(f"  • Collection size: {qd_stats.get('vectors_count', 0)}")
    
    print("="*60 + "\n")
    
    return {
        'success': True,
        'documents_processed': successful_docs,
        'total_chunks': total_chunks,
        'processing_time': total_time
    }


if __name__ == "__main__":
    try:
        result = asyncio.run(run_fast_pipeline())
        
        if result['success']:
            print(f"✅ Pipeline completed successfully!")
        else:
            print(f"❌ Pipeline failed")
            
    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        print(f"❌ Pipeline failed: {e}")