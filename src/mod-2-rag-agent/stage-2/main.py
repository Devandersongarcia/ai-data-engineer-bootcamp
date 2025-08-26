"""
Main execution script for the RAG ingestion pipeline.

This script provides a CLI interface for running the complete
document processing pipeline with various options.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from config import load_settings, Settings
from pipeline import RAGIngestionPipeline
from data_loader import MinIODocumentLoader


async def validate_connections(settings: Settings):
    """
    Validate all service connections.
    
    Args:
        settings: Application settings
    """
    logger.info("Validating service connections...")
    
    pipeline = RAGIngestionPipeline(settings)
    validation = pipeline.validate_pipeline()
    
    print("\n" + "="*50)
    print("Service Connection Status:")
    print("="*50)
    print(f"✓ MinIO:     {'✅' if validation['minio'] else '❌'}")
    print(f"✓ OpenAI:    {'✅' if validation['openai'] else '❌'}")
    print(f"✓ Pinecone:  {'✅' if validation['pinecone'] else '❌'}")
    print(f"✓ Qdrant:    {'✅' if validation['qdrant'] else '❌'}")
    
    if validation['issues']:
        print("\n⚠️  Issues found:")
        for issue in validation['issues']:
            print(f"   - {issue}")
    
    print("="*50 + "\n")
    
    return validation['all_valid']


async def list_documents(settings: Settings):
    """
    List all documents in MinIO.
    
    Args:
        settings: Application settings
    """
    loader = MinIODocumentLoader(settings)
    files = loader.list_docx_files()
    
    print("\n" + "="*50)
    print(f"Documents in MinIO ({len(files)} total):")
    print("="*50)
    
    for i, file in enumerate(files, 1):
        size_mb = file['size'] / (1024 * 1024)
        print(f"{i:3}. {file['name']:<30} ({size_mb:.2f} MB)")
    
    print("="*50 + "\n")


async def process_single_document(settings: Settings, document_name: str):
    """
    Process a single document.
    
    Args:
        settings: Application settings
        document_name: Name of the document to process
    """
    logger.info(f"Processing single document: {document_name}")
    
    pipeline = RAGIngestionPipeline(settings)
    loader = MinIODocumentLoader(settings)
    
    try:
        # Load specific document
        documents = loader.load_specific_document(document_name)
        
        if not documents:
            logger.error(f"Document not found: {document_name}")
            return
        
        # Process document
        result = await pipeline.process_document(documents[0])
        
        # Print results
        print("\n" + "="*50)
        print(f"Document Processing Results: {document_name}")
        print("="*50)
        print(f"Status: {result['status']}")
        
        if result['status'] == 'completed':
            for stage, info in result['stages'].items():
                print(f"\n{stage.title()}:")
                for key, value in info.items():
                    print(f"  - {key}: {value}")
        else:
            print(f"\n❌ Processing failed:")
            for error in result['errors']:
                print(f"  - {error}")
        
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to process document: {e}")


async def run_full_pipeline(settings: Settings):
    """
    Run the complete pipeline on all documents.
    
    Args:
        settings: Application settings
    """
    pipeline = RAGIngestionPipeline(settings)
    
    # Run pipeline
    results = await pipeline.run_full_pipeline()
    
    # Print summary
    print("\n" + "="*60)
    print("Pipeline Execution Summary")
    print("="*60)
    
    if results['status'] == 'completed':
        docs = results['documents']
        stats = results['pipeline_stats']
        
        print(f"\n📊 Document Processing:")
        print(f"   Total Documents:     {docs['total']}")
        print(f"   Successful:          {docs['successful']} ✅")
        print(f"   Failed:              {docs['failed']} ❌")
        
        print(f"\n📈 Pipeline Statistics:")
        print(f"   Total Chunks:        {stats['total_chunks']}")
        print(f"   Total Embeddings:    {stats['total_embeddings']}")
        print(f"   Execution Time:      {results['execution_time_seconds']:.2f} seconds")
        
        if 'embedding_stats' in results:
            emb_stats = results['embedding_stats']
            print(f"\n🔤 Embedding Statistics:")
            print(f"   Cache Hit Ratio:     {emb_stats.get('cache_hit_ratio', 0):.2%}")
            print(f"   API Calls:           {emb_stats.get('api_calls', 0)}")
            print(f"   Estimated Cost:      ${emb_stats.get('estimated_cost_usd', 0):.4f}")
        
        if 'vector_store_stats' in results:
            vs_stats = results['vector_store_stats']
            
            if 'pinecone' in vs_stats:
                pc_stats = vs_stats['pinecone']
                print(f"\n📍 Pinecone Statistics:")
                print(f"   Total Ingested:      {pc_stats.get('total_ingested', 0)}")
                print(f"   Failed:              {pc_stats.get('failed_ingestions', 0)}")
            
            if 'qdrant' in vs_stats:
                qd_stats = vs_stats['qdrant']
                print(f"\n🎯 Qdrant Statistics:")
                print(f"   Total Ingested:      {qd_stats.get('total_ingested', 0)}")
                print(f"   Failed:              {qd_stats.get('failed_ingestions', 0)}")
        
        print(f"\n💾 Results saved to: pipeline_results.json")
    else:
        print(f"\n❌ Pipeline failed: {results.get('error', 'Unknown error')}")
    
    print("="*60 + "\n")


async def clear_caches(settings: Settings):
    """
    Clear all caches.
    
    Args:
        settings: Application settings
    """
    from embeddings import OptimizedEmbeddingGenerator
    
    logger.info("Clearing caches...")
    
    generator = OptimizedEmbeddingGenerator(settings)
    generator.clear_cache()
    
    print("\n✅ Caches cleared successfully\n")


def main():
    """
    Main CLI entry point.
    """
    parser = argparse.ArgumentParser(
        description="RAG Ingestion Pipeline - Process DOCX files from MinIO to vector stores"
    )
    
    parser.add_argument(
        'action',
        choices=['run', 'validate', 'list', 'process', 'clear-cache'],
        help='Action to perform'
    )
    
    parser.add_argument(
        '--document',
        type=str,
        help='Document name for single document processing'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        default='.env',
        help='Path to environment file (default: .env)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Load settings
    if args.env:
        import os
        os.environ['ENV_FILE'] = args.env
    
    settings = load_settings()
    
    # Set logging level
    if args.verbose:
        logger.level("DEBUG")
    
    # Print header
    print("\n" + "="*60)
    print("🚀 RAG Ingestion Pipeline v1.0")
    print("="*60)
    
    # Execute action
    try:
        if args.action == 'validate':
            asyncio.run(validate_connections(settings))
        
        elif args.action == 'list':
            asyncio.run(list_documents(settings))
        
        elif args.action == 'process':
            if not args.document:
                print("❌ Error: --document required for process action")
                sys.exit(1)
            asyncio.run(process_single_document(settings, args.document))
        
        elif args.action == 'run':
            # Validate first
            valid = asyncio.run(validate_connections(settings))
            if not valid:
                print("❌ Cannot run pipeline: service validation failed")
                sys.exit(1)
            
            # Run pipeline
            asyncio.run(run_full_pipeline(settings))
        
        elif args.action == 'clear-cache':
            asyncio.run(clear_caches(settings))
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()