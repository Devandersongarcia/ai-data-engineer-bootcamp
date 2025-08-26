"""
Main RAG pipeline orchestrator.

This module coordinates the entire preprocessing, chunking, embedding,
and ingestion pipeline for end-to-end document processing.
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from datetime import datetime
import json

from llama_index.core import Document
from llama_index.llms.openai import OpenAI
from loguru import logger
from tqdm import tqdm

from config import Settings, load_settings
from data_loader import MinIODocumentLoader
from preprocessors import DocumentPreprocessor
from metadata_extractors import MetadataEnricher
from chunking_strategies import SmartChunkingPipeline
from embeddings import OptimizedEmbeddingGenerator, EmbeddingValidator
from vector_stores import DualVectorStoreManager


class RAGIngestionPipeline:
    """
    Complete RAG ingestion pipeline orchestrator.
    
    Manages the full document processing flow from MinIO storage
    through preprocessing, chunking, embedding, and vector store ingestion.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize RAG ingestion pipeline.
        
        Args:
            settings: Optional settings override
        """
        self.settings = settings or load_settings()
        
        # Set up logging
        self._setup_logging()
        
        # Initialize components
        logger.info("Initializing RAG Ingestion Pipeline...")
        self.loader = MinIODocumentLoader(self.settings)
        self.preprocessor = DocumentPreprocessor()
        self.metadata_enricher = MetadataEnricher(self.settings)
        self.chunking_pipeline = SmartChunkingPipeline(self.settings)
        self.embedding_generator = OptimizedEmbeddingGenerator(self.settings)
        self.embedding_validator = EmbeddingValidator(self.settings.openai.embedding_dimensions)
        self.vector_store_manager = DualVectorStoreManager(self.settings)
        
        # Pipeline statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'documents_processed': 0,
            'documents_failed': 0,
            'total_chunks': 0,
            'total_embeddings': 0,
            'pipeline_errors': []
        }
        
        logger.info("Pipeline initialized successfully")
    
    def _setup_logging(self):
        """Configure pipeline logging."""
        log_file = self.settings.log_file
        log_level = self.settings.log_level
        
        logger.add(
            log_file,
            rotation="100 MB",
            retention="7 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
        )
    
    async def process_document(self, document: Document) -> Dict[str, Any]:
        """
        Process single document through the entire pipeline.
        
        Args:
            document: Document to process
            
        Returns:
            Processing results dictionary
        """
        doc_id = document.metadata.get('filename', 'unknown')
        logger.info(f"Processing document: {doc_id}")
        
        result = {
            'document_id': doc_id,
            'status': 'processing',
            'stages': {},
            'errors': []
        }
        
        try:
            # Stage 1: Preprocessing
            logger.debug(f"Stage 1: Preprocessing {doc_id}")
            preprocessed_doc = self.preprocessor.preprocess_document(document)
            result['stages']['preprocessing'] = {
                'status': 'completed',
                'reduction_pct': preprocessed_doc.metadata.get('preprocessing', {}).get('reduction_percentage', 0)
            }
            
            # Stage 2: Metadata Enrichment
            logger.debug(f"Stage 2: Enriching metadata for {doc_id}")
            enriched_doc = await self.metadata_enricher.enrich_document(preprocessed_doc)
            result['stages']['enrichment'] = {
                'status': 'completed',
                'metadata_keys': list(enriched_doc.metadata.keys())
            }
            
            # Stage 3: Chunking
            logger.debug(f"Stage 3: Chunking {doc_id}")
            chunks_data = self.chunking_pipeline.chunk_document(enriched_doc)
            
            # Flatten all chunk types
            all_chunks = []
            all_chunks.extend(chunks_data['semantic_chunks'])
            all_chunks.extend(chunks_data['retrieval_chunks'])
            all_chunks.extend(chunks_data['synthesis_chunks'])
            for level_chunks in chunks_data['hierarchical_chunks'].values():
                all_chunks.extend(level_chunks)
            
            result['stages']['chunking'] = {
                'status': 'completed',
                'total_chunks': len(all_chunks),
                'chunk_types': {
                    'semantic': len(chunks_data['semantic_chunks']),
                    'retrieval': len(chunks_data['retrieval_chunks']),
                    'synthesis': len(chunks_data['synthesis_chunks']),
                    'hierarchical': sum(len(v) for v in chunks_data['hierarchical_chunks'].values())
                }
            }
            
            # Stage 4: Embedding Generation
            logger.debug(f"Stage 4: Generating embeddings for {doc_id}")
            embedded_chunks = await self.embedding_generator.generate_chunk_embeddings(
                all_chunks, 
                strategy="adaptive"
            )
            
            # Validate embeddings
            valid_chunks = []
            for chunk in embedded_chunks:
                if chunk.embedding is not None:
                    is_valid, issues = self.embedding_validator.validate_embedding(chunk.embedding)
                    if is_valid:
                        valid_chunks.append(chunk)
                    else:
                        logger.warning(f"Invalid embedding for chunk {chunk.id}: {issues}")
            
            result['stages']['embedding'] = {
                'status': 'completed',
                'total_embeddings': len(embedded_chunks),
                'valid_embeddings': len(valid_chunks),
                'cache_hit_ratio': self.embedding_generator.stats.get('cache_hit_ratio', 0)
            }
            
            # Stage 5: Vector Store Ingestion
            logger.debug(f"Stage 5: Ingesting to vector stores for {doc_id}")
            ingestion_results = await self.vector_store_manager.ingest_chunks(
                valid_chunks,
                strategy="both"
            )
            
            result['stages']['ingestion'] = {
                'status': 'completed',
                'results': ingestion_results
            }
            
            # Update statistics
            self.stats['documents_processed'] += 1
            self.stats['total_chunks'] += len(all_chunks)
            self.stats['total_embeddings'] += len(valid_chunks)
            
            result['status'] = 'completed'
            logger.info(f"Successfully processed document: {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            result['status'] = 'failed'
            result['errors'].append(str(e))
            self.stats['documents_failed'] += 1
            self.stats['pipeline_errors'].append({
                'document': doc_id,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return result
    
    async def process_batch(
        self, 
        documents: List[Document],
        concurrent: bool = True,
        max_concurrent: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Process batch of documents.
        
        Args:
            documents: List of documents to process
            concurrent: Whether to process concurrently
            max_concurrent: Maximum concurrent processing
            
        Returns:
            List of processing results
        """
        logger.info(f"Processing batch of {len(documents)} documents")
        results = []
        
        if concurrent:
            # Process concurrently with semaphore for rate limiting
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(doc):
                async with semaphore:
                    return await self.process_document(doc)
            
            tasks = [process_with_semaphore(doc) for doc in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    doc_id = documents[i].metadata.get('filename', f'doc_{i}')
                    processed_results.append({
                        'document_id': doc_id,
                        'status': 'failed',
                        'errors': [str(result)]
                    })
                else:
                    processed_results.append(result)
            results = processed_results
        else:
            # Process sequentially
            for doc in tqdm(documents, desc="Processing documents"):
                result = await self.process_document(doc)
                results.append(result)
        
        return results
    
    async def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete pipeline on all documents in MinIO.
        
        Returns:
            Pipeline execution summary
        """
        self.stats['start_time'] = datetime.utcnow()
        logger.info("Starting full pipeline execution")
        
        try:
            # Load all documents
            logger.info("Loading documents from MinIO...")
            documents = list(self.loader.load_all_documents())
            logger.info(f"Loaded {len(documents)} documents")
            
            if not documents:
                logger.warning("No documents found in MinIO")
                return {
                    'status': 'completed',
                    'message': 'No documents to process',
                    'stats': self.stats
                }
            
            # Process documents
            results = await self.process_batch(
                documents,
                concurrent=True,
                max_concurrent=self.settings.performance.max_workers
            )
            
            # Analyze results
            successful = sum(1 for r in results if r['status'] == 'completed')
            failed = sum(1 for r in results if r['status'] == 'failed')
            
            self.stats['end_time'] = datetime.utcnow()
            execution_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            # Get component statistics
            embedding_stats = self.embedding_generator.get_statistics()
            vector_store_stats = self.vector_store_manager.get_statistics()
            
            summary = {
                'status': 'completed',
                'execution_time_seconds': execution_time,
                'documents': {
                    'total': len(documents),
                    'successful': successful,
                    'failed': failed
                },
                'pipeline_stats': self.stats,
                'embedding_stats': embedding_stats,
                'vector_store_stats': vector_store_stats,
                'results': results
            }
            
            # Save summary to file
            summary_file = Path('./pipeline_results.json')
            with summary_file.open('w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"Pipeline completed: {successful}/{len(documents)} documents processed successfully")
            
            return summary
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            self.stats['end_time'] = datetime.utcnow()
            return {
                'status': 'failed',
                'error': str(e),
                'stats': self.stats
            }
    
    def validate_pipeline(self) -> Dict[str, Any]:
        """
        Validate pipeline configuration and connections.
        
        Returns:
            Validation results
        """
        logger.info("Validating pipeline configuration...")
        
        validation = {
            'minio': False,
            'openai': False,
            'pinecone': False,
            'qdrant': False,
            'issues': []
        }
        
        # Test MinIO connection
        try:
            files = self.loader.list_docx_files()
            validation['minio'] = True
            logger.info(f"MinIO connection valid: {len(files)} files found")
        except Exception as e:
            validation['issues'].append(f"MinIO connection failed: {e}")
        
        # Test OpenAI
        try:
            # Test with a simple OpenAI call instead of async
            from openai import OpenAI as OpenAIClient
            client = OpenAIClient(api_key=self.settings.openai.api_key)
            # Test the API key by making a simple request
            response = client.models.list()
            if response:
                validation['openai'] = True
                logger.info("OpenAI connection valid")
        except Exception as e:
            validation['issues'].append(f"OpenAI connection failed: {e}")
        
        # Test Pinecone
        try:
            stats = self.vector_store_manager.pinecone_ingester.get_statistics()
            validation['pinecone'] = True
            logger.info("Pinecone connection valid")
        except Exception as e:
            validation['issues'].append(f"Pinecone connection failed: {e}")
        
        # Test Qdrant
        try:
            stats = self.vector_store_manager.qdrant_ingester.get_statistics()
            validation['qdrant'] = True
            logger.info("Qdrant connection valid")
        except Exception as e:
            validation['issues'].append(f"Qdrant connection failed: {e}")
        
        validation['all_valid'] = all([
            validation['minio'],
            validation['openai'],
            validation['pinecone'],
            validation['qdrant']
        ])
        
        return validation


async def main():
    """
    Main entry point for pipeline execution.
    """
    # Load settings
    settings = load_settings()
    
    # Initialize pipeline
    pipeline = RAGIngestionPipeline(settings)
    
    # Validate configuration
    validation = pipeline.validate_pipeline()
    
    if not validation['all_valid']:
        logger.error(f"Pipeline validation failed: {validation['issues']}")
        return
    
    logger.info("Pipeline validation successful")
    
    # Run full pipeline
    results = await pipeline.run_full_pipeline()
    
    # Print summary
    if results['status'] == 'completed':
        print(f"\n✅ Pipeline completed successfully!")
        print(f"   Documents processed: {results['documents']['successful']}/{results['documents']['total']}")
        print(f"   Total chunks created: {results['pipeline_stats']['total_chunks']}")
        print(f"   Total embeddings generated: {results['pipeline_stats']['total_embeddings']}")
        print(f"   Execution time: {results['execution_time_seconds']:.2f} seconds")
        print(f"\n📊 Results saved to: pipeline_results.json")
    else:
        print(f"\n❌ Pipeline failed: {results.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())