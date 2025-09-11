#!/usr/bin/env python
"""
Precompute embeddings for all questions to improve semantic search performance
This script loads questions and precomputes their embeddings using sentence-transformers
"""

import sys
import json
import logging
from pathlib import Path
import time
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.selection.enhanced_embedding_service import EnhancedEmbeddingService
from app.services.question_bank import QuestionBank

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_questions_from_json(file_path: str) -> List[Dict[str, Any]]:
    """Load questions from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract questions based on structure
        questions = []
        
        # Handle different JSON structures
        if isinstance(data, dict):
            # If it's the v2_full structure with PNMs
            for pnm_key, pnm_data in data.items():
                if isinstance(pnm_data, dict) and 'Questions' in pnm_data:
                    for q in pnm_data['Questions']:
                        q['pnm'] = pnm_key
                        questions.append(q)
        elif isinstance(data, list):
            # If it's a flat list of questions
            questions = data
            
        logger.info(f"Loaded {len(questions)} questions from {file_path}")
        return questions
        
    except Exception as e:
        logger.error(f"Failed to load questions from {file_path}: {e}")
        return []


def precompute_for_question_bank():
    """Precompute embeddings using QuestionBank"""
    logger.info("=== Precomputing embeddings for QuestionBank ===")
    
    try:
        # Initialize question bank
        qb = QuestionBank(source='v2_full')
        
        # Get all questions
        all_questions = []
        for pnm in qb.list_pnms():
            for term in qb.list_terms(pnm):
                questions = qb.search_by_pnm_term(pnm, term)
                all_questions.extend(questions)
        
        logger.info(f"Found {len(all_questions)} questions in QuestionBank")
        
        # Initialize embedding service with medical model
        embedding_service = EnhancedEmbeddingService(model_type='medical')
        
        # Precompute embeddings
        embedding_service.precompute_embeddings(
            all_questions,
            text_fields=['main', 'Prompt_Main', 'question'],
            batch_size=32
        )
        
        # Show cache statistics
        stats = embedding_service.get_cache_stats()
        logger.info(f"Cache statistics: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to precompute for QuestionBank: {e}")
        return False


def precompute_for_json_files():
    """Precompute embeddings for all JSON question files"""
    logger.info("=== Precomputing embeddings for JSON files ===")
    
    # Define question file paths
    question_files = [
        "app/data/pnm_questions_v2_full.json",
        "app/data/pnm_questions_v3_final.json",
        "app/data/pnm_questions_v3_enhanced.json"
    ]
    
    # Initialize embedding service
    embedding_service = EnhancedEmbeddingService(model_type='medical')
    
    for file_path in question_files:
        full_path = Path(file_path)
        if full_path.exists():
            logger.info(f"Processing {file_path}...")
            questions = load_questions_from_json(full_path)
            
            if questions:
                embedding_service.precompute_embeddings(
                    questions,
                    text_fields=['Prompt_Main', 'main', 'question'],
                    batch_size=32
                )
        else:
            logger.warning(f"File not found: {file_path}")
    
    # Show final cache statistics
    stats = embedding_service.get_cache_stats()
    logger.info(f"Final cache statistics: {stats}")


def test_semantic_search():
    """Test semantic search with precomputed embeddings"""
    logger.info("=== Testing semantic search ===")
    
    # Initialize services
    embedding_service = EnhancedEmbeddingService(model_type='medical')
    qb = QuestionBank(source='v2_full')
    
    # Test queries
    test_queries = [
        "difficulty breathing at night",
        "trouble swallowing liquids",
        "falling when walking",
        "can't speak clearly anymore",
        "hands are getting weaker"
    ]
    
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        
        # Get all questions for testing
        all_questions = []
        for pnm in qb.list_pnms()[:2]:  # Test with first 2 PNMs
            for term in qb.list_terms(pnm)[:2]:  # Test with first 2 terms
                questions = qb.search_by_pnm_term(pnm, term)
                all_questions.extend(questions)
        
        # Find similar questions
        similar = embedding_service.find_similar_questions(
            query=query,
            questions=all_questions,
            top_k=3,
            threshold=0.3
        )
        
        # Display results
        for i, (question, score) in enumerate(similar, 1):
            logger.info(f"  {i}. [Score: {score:.3f}] {question.get('main', '')[:100]}...")


def compare_models():
    """Compare different embedding models"""
    logger.info("=== Comparing embedding models ===")
    
    test_text = "I have difficulty breathing when lying down at night"
    
    model_types = ['english', 'medical', 'high_quality']
    
    for model_type in model_types:
        logger.info(f"\nTesting {model_type} model...")
        
        # Initialize service
        service = EnhancedEmbeddingService(model_type=model_type)
        
        # Measure encoding time
        start_time = time.time()
        embedding = service.get_embedding(test_text, use_cache=False)
        encode_time = time.time() - start_time
        
        logger.info(f"  Model: {service.model_name}")
        logger.info(f"  Embedding dimension: {len(embedding)}")
        logger.info(f"  Encoding time: {encode_time:.3f} seconds")
        
        # Test similarity
        similar_text = "Breathing problems when sleeping"
        different_text = "My hands are getting weaker"
        
        sim_score = service.semantic_similarity(test_text, similar_text)
        diff_score = service.semantic_similarity(test_text, different_text)
        
        logger.info(f"  Similarity to related text: {sim_score:.3f}")
        logger.info(f"  Similarity to different text: {diff_score:.3f}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Precompute embeddings for questions")
    parser.add_argument(
        '--mode', 
        choices=['questionbank', 'json', 'test', 'compare', 'all'],
        default='all',
        help='Precomputation mode'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear existing cache before precomputation'
    )
    
    args = parser.parse_args()
    
    # Clear cache if requested
    if args.clear_cache:
        logger.info("Clearing existing cache...")
        service = EnhancedEmbeddingService(model_type='medical')
        service.clear_cache()
    
    # Run based on mode
    if args.mode == 'questionbank':
        precompute_for_question_bank()
    elif args.mode == 'json':
        precompute_for_json_files()
    elif args.mode == 'test':
        test_semantic_search()
    elif args.mode == 'compare':
        compare_models()
    elif args.mode == 'all':
        # Run all modes
        precompute_for_question_bank()
        precompute_for_json_files()
        test_semantic_search()
        
    logger.info("\n=== Precomputation complete ===")


if __name__ == "__main__":
    main()