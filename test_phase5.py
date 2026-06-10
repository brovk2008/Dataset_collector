#!/usr/bin/env python
"""Phase 5 Integration Testing - Non-GUI validation."""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test critical imports."""
    print("=" * 60)
    print("TEST 1: Import Validation")
    print("=" * 60)

    try:
        from dataset_collector.core.models import DatasetResult
        print("[OK] DatasetResult")
        from dataset_collector.databrain.semantic_ranker import SemanticRanker
        print("[OK] SemanticRanker")
        from dataset_collector.databrain.health_score import HealthScorer
        print("[OK] HealthScorer")
        from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
        print("[OK] EmbeddingsCache")
        from dataset_collector.databrain.user_behavior import UserBehaviorTracker
        print("[OK] UserBehaviorTracker")
        from dataset_collector.search.relevance import compute_hybrid_rank_score
        print("[OK] compute_hybrid_rank_score")
        print("\n[OK] All critical imports successful\n")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}\n")
        return False

def test_models():
    """Test DatasetResult model enhancements."""
    print("=" * 60)
    print("TEST 2: DatasetResult Model")
    print("=" * 60)

    try:
        from dataset_collector.core.models import DatasetResult
        from dataset_collector.core.enums import DataSource

        result = DatasetResult(
            id="test-1",
            name="Test Dataset",
            description="A test dataset",
            source=DataSource.KAGGLE,
            url="https://example.com",
            estimated_size_bytes=1000000,
            relevance_score=0.85,
            quality_score=8,
        )

        # Check new fields
        assert hasattr(result, 'semantic_score'), "Missing semantic_score field"
        assert hasattr(result, 'click_score'), "Missing click_score field"
        assert hasattr(result, 'health_score'), "Missing health_score field"

        print(f"[OK] semantic_score field exists (default: {result.semantic_score})")
        print(f"[OK] click_score field exists (default: {result.click_score})")
        print(f"[OK] health_score field exists (default: {result.health_score})")

        # Test setting values
        result.semantic_score = 0.92
        result.click_score = 0.15
        result.health_score = 85

        print(f"[OK] Can set semantic_score: {result.semantic_score}")
        print(f"[OK] Can set click_score: {result.click_score}")
        print(f"[OK] Can set health_score: {result.health_score}\n")
        return True
    except Exception as e:
        print(f"[FAIL] Model test failed: {e}\n")
        return False

def test_health_scoring():
    """Test health score computation."""
    print("=" * 60)
    print("TEST 3: Health Score Computation")
    print("=" * 60)

    try:
        from dataset_collector.core.models import DatasetResult
        from dataset_collector.core.enums import DataSource
        from dataset_collector.databrain.health_score import HealthScorer

        scorer = HealthScorer()

        # Create a well-documented dataset
        good_dataset = DatasetResult(
            id="good-1",
            name="Well-Documented Dataset",
            description="This is a comprehensive and well-documented dataset with lots of metadata and information about its contents.",
            source=DataSource.KAGGLE,
            url="https://example.com/good",
            estimated_size_bytes=1000000,
            license_info="CC BY 4.0",
            last_updated=datetime.now(timezone.utc),
            metadata={
                "tags": "machine learning, classification",
                "category": "Computer Vision",
                "downloads": 50000,
                "stars": 500,
            },
        )

        # Create a poorly documented dataset
        poor_dataset = DatasetResult(
            id="poor-1",
            name="Minimal Dataset",
            description="Data",
            source=DataSource.GITHUB,
            url="https://example.com/poor",
            estimated_size_bytes=100000,
            license_info="Unknown",
            metadata={},
        )

        good_score = scorer.compute_health_score(good_dataset)
        poor_score = scorer.compute_health_score(poor_dataset)

        print(f"[OK] Well-documented dataset score: {good_score}/100")
        print(f"[OK] Poorly-documented dataset score: {poor_score}/100")
        assert good_score > poor_score, "Good dataset should score higher"
        print(f"[OK] Good dataset scores higher: {good_score} > {poor_score}")

        # Test labels
        print(f"[OK] Label for {good_score}: {scorer.get_health_label(good_score)}")
        print(f"[OK] Label for {poor_score}: {scorer.get_health_label(poor_score)}\n")
        return True
    except Exception as e:
        print(f"[FAIL] Health score test failed: {e}\n")
        return False

def test_hybrid_ranking():
    """Test hybrid ranking with semantic + keyword + other factors."""
    print("=" * 60)
    print("TEST 4: Hybrid Ranking")
    print("=" * 60)

    try:
        from dataset_collector.core.models import DatasetResult
        from dataset_collector.core.enums import DataSource
        from dataset_collector.search.relevance import compute_hybrid_rank_score

        result = DatasetResult(
            id="test-1",
            name="Machine Learning Dataset",
            description="Features and labels for ML models",
            source=DataSource.KAGGLE,
            url="https://example.com",
            estimated_size_bytes=1000000,
            last_updated=datetime.now(timezone.utc),
            metadata={"downloads": 5000, "stars": 100},
        )

        # Set component scores
        result.relevance_score = 0.90  # 40% weight = 36 points
        result.semantic_score = 0.88   # 40% weight = 35.2 points
        result.click_score = 0.20      # 5% weight = 1 point
        # popularity: ~0.65, freshness: ~0.98 calculated internally

        score = compute_hybrid_rank_score("machine learning", result)
        print(f"[OK] Hybrid rank score: {score}/100")

        # Score should incorporate all components
        assert 50 < score < 100, f"Score should be reasonable (50-100), got {score}"
        print(f"[OK] Score is in expected range\n")
        return True
    except Exception as e:
        print(f"[FAIL] Hybrid ranking test failed: {e}\n")
        return False

def test_cache_initialization():
    """Test embeddings and behavior tracking DB initialization."""
    print("=" * 60)
    print("TEST 5: Cache Initialization")
    print("=" * 60)

    try:
        from pathlib import Path
        import tempfile
        from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
        from dataset_collector.databrain.user_behavior import UserBehaviorTracker

        # Use temp directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Test embeddings cache
            emb_cache = EmbeddingsCache(cache_dir)
            print(f"[OK] EmbeddingsCache created at {emb_cache._db_path}")
            stats = emb_cache.stats()
            print(f"[OK] Cache stats: {stats['total_cached']} cached, {stats['total_size_mb']:.1f} MB")
            emb_cache.close()

            # Test behavior tracker
            behavior = UserBehaviorTracker(cache_dir)
            print(f"[OK] UserBehaviorTracker created at {behavior._db_path}")
            search_id = behavior.log_search("machine learning", ["Kaggle"], 10)
            print(f"[OK] Logged search with ID: {search_id}")
            behavior.log_click(search_id, "dataset-1", 0, "table")
            print(f"[OK] Logged click on dataset-1")
            behavior.close()

        print("[OK] All cache operations successful\n")
        return True
    except Exception as e:
        print(f"[FAIL] Cache initialization test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print(" Phase 5 Integration Testing ".center(60))
    print("=" * 60)
    print()

    tests = [
        ("Import Validation", test_imports),
        ("DatasetResult Model", test_models),
        ("Health Scoring", test_health_scoring),
        ("Hybrid Ranking", test_hybrid_ranking),
        ("Cache Initialization", test_cache_initialization),
    ]

    results = []
    for name, test_func in tests:
        try:
            results.append((name, test_func()))
        except Exception as e:
            print(f"[FAIL] {name} crashed: {e}\n")
            results.append((name, False))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status}: {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\n{passed_count}/{total_count} tests passed")

    return all(p for _, p in results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
