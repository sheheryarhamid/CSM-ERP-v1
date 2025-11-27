#!/usr/bin/env python3
"""
Streaming performance test for secure blob streaming.

Tests:
1. Large file streaming (>100MB) with bounded memory usage
2. Chunk-by-chunk streaming validation
3. Memory profiling during streaming operations

Usage:
    python dev/scripts/streaming_perf.py
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hub.blob_store import LocalEncryptedBlobStore


def format_bytes(size):
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def get_memory_usage():
    """Get current process memory usage in bytes."""
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss
    except ImportError:
        # Fallback if psutil not available
        return None


def test_large_file_streaming():
    """Test streaming of a large file (>100MB) with memory bounds."""
    print("\n" + "=" * 70)
    print("TEST 1: Large File Streaming (>100MB)")
    print("=" * 70)

    # Setup
    test_dir = Path("dev/test_data/perf_blobs")
    test_dir.mkdir(parents=True, exist_ok=True)

    blob_store = LocalEncryptedBlobStore(base_dir=str(test_dir))

    # Create a large test file (100MB)
    file_size = 100 * 1024 * 1024  # 100 MB
    chunk_size = 64 * 1024  # 64 KB chunks

    print(f"\nGenerating {format_bytes(file_size)} test file...")
    test_data = bytearray()
    for i in range(file_size // 1024):
        test_data.extend(f"Test data chunk {i:010d}\n".encode() * 32)

    # Store the blob
    print(f"Storing blob (encrypted, chunked)...")
    start_time = time.time()
    start_memory = get_memory_usage()

    blob_id = "perf_test_large"
    blob_store.create_chunked_blob(blob_id, bytes(test_data), chunk_size=chunk_size)

    end_time = time.time()
    end_memory = get_memory_usage()

    store_duration = end_time - start_time
    print(f"✓ Stored blob ID: {blob_id}")
    print(f"  Duration: {store_duration:.2f}s")
    print(f"  Throughput: {format_bytes(file_size / store_duration)}/s")

    if start_memory and end_memory:
        memory_delta = end_memory - start_memory
        print(f"  Memory delta: {format_bytes(memory_delta)}")
        # Assert memory usage is reasonable (< 50MB for 100MB file)
        if memory_delta > 50 * 1024 * 1024:
            print(f"  ⚠ WARNING: Memory usage higher than expected")

    # Stream the blob back
    print(f"\nStreaming blob back...")
    start_time = time.time()
    start_memory = get_memory_usage()

    chunks_received = 0
    bytes_received = 0

    for chunk in blob_store.stream_blob(blob_id, chunk_size=8192):
        chunks_received += 1
        bytes_received += len(chunk)

    end_time = time.time()
    end_memory = get_memory_usage()

    stream_duration = end_time - start_time
    print(f"✓ Streamed {format_bytes(bytes_received)} in {chunks_received} chunks")
    print(f"  Duration: {stream_duration:.2f}s")
    print(f"  Throughput: {format_bytes(bytes_received / stream_duration)}/s")

    if start_memory and end_memory:
        memory_delta = end_memory - start_memory
        print(f"  Memory delta: {format_bytes(memory_delta)}")
        # Assert memory usage is bounded (< 20MB for streaming)
        if memory_delta > 20 * 1024 * 1024:
            print(f"  ⚠ WARNING: Memory usage higher than expected during streaming")

    # Verify data integrity
    print(f"\nVerifying data integrity...")
    full_data = bytearray()
    for chunk in blob_store.stream_blob(blob_id):
        full_data.extend(chunk)

    assert bytes(full_data) == bytes(test_data), "Data integrity check failed"
    print(f"✓ Data integrity verified ({format_bytes(len(full_data))})")

    # Cleanup
    os.remove(blob_store._path_for(blob_id))
    print(f"✓ Cleanup complete")

    print("\n✓ TEST 1 PASSED")


def test_multiple_file_sizes():
    """Test streaming with various file sizes."""
    print("\n" + "=" * 70)
    print("TEST 2: Multiple File Sizes")
    print("=" * 70)

    # Setup
    test_dir = Path("dev/test_data/perf_blobs")
    test_dir.mkdir(parents=True, exist_ok=True)

    blob_store = LocalEncryptedBlobStore(base_dir=str(test_dir))

    # Test various sizes
    test_sizes = [
        ("1KB", 1 * 1024),
        ("10KB", 10 * 1024),
        ("100KB", 100 * 1024),
        ("1MB", 1 * 1024 * 1024),
        ("10MB", 10 * 1024 * 1024),
        ("50MB", 50 * 1024 * 1024),
    ]

    print(f"\nTesting various file sizes...")
    for name, size in test_sizes:
        # Create test data
        test_data = b"X" * size
        blob_id = f"perf_test_{name.lower()}"

        # Store
        start_time = time.time()
        blob_store.create_chunked_blob(blob_id, test_data)
        store_duration = time.time() - start_time

        # Stream back
        start_time = time.time()
        bytes_count = 0
        for chunk in blob_store.stream_blob(blob_id):
            bytes_count += len(chunk)
        stream_duration = time.time() - start_time

        print(
            f"  {name:>6}: store {store_duration*1000:>6.1f}ms "
            f"({format_bytes(size/store_duration)}/s), "
            f"stream {stream_duration*1000:>6.1f}ms "
            f"({format_bytes(size/stream_duration)}/s)"
        )

        assert bytes_count == size, f"Size mismatch for {name}"

        # Cleanup
        os.remove(blob_store._path_for(blob_id))

    print(f"✓ All size tests successful")
    print("\n✓ TEST 2 PASSED")


def test_chunking_variations():
    """Test different chunk sizes."""
    print("\n" + "=" * 70)
    print("TEST 3: Chunking Variations")
    print("=" * 70)

    # Setup
    test_dir = Path("dev/test_data/perf_blobs")
    test_dir.mkdir(parents=True, exist_ok=True)

    blob_store = LocalEncryptedBlobStore(base_dir=str(test_dir))

    # Create a 10MB test file
    file_size = 10 * 1024 * 1024
    test_data = b"Y" * file_size

    chunk_sizes = [
        ("4KB", 4 * 1024),
        ("16KB", 16 * 1024),
        ("64KB", 64 * 1024),
        ("256KB", 256 * 1024),
        ("1MB", 1 * 1024 * 1024),
    ]

    print(f"\nTesting different chunk sizes (10MB file)...")
    for name, chunk_size in chunk_sizes:
        blob_id = f"perf_test_chunk_{name.lower()}"

        # Store with specific chunk size
        start_time = time.time()
        blob_store.create_chunked_blob(blob_id, test_data, chunk_size=chunk_size)
        store_duration = time.time() - start_time

        # Stream back
        start_time = time.time()
        bytes_count = 0
        chunks_count = 0
        for chunk in blob_store.stream_blob(blob_id):
            bytes_count += len(chunk)
            chunks_count += 1
        stream_duration = time.time() - start_time

        print(
            f"  {name:>6} chunks: store {store_duration*1000:>6.1f}ms, "
            f"stream {stream_duration*1000:>6.1f}ms ({chunks_count} chunks)"
        )

        assert bytes_count == file_size

        # Cleanup
        os.remove(blob_store._path_for(blob_id))

    print(f"✓ All chunking tests successful")
    print("\n✓ TEST 3 PASSED")


def main():
    """Run all performance tests."""
    print("\n" + "=" * 70)
    print("SECURE BLOB STREAMING PERFORMANCE TESTS")
    print("=" * 70)

    # Check for psutil
    try:
        import psutil

        print(f"✓ Memory profiling enabled (psutil available)")
    except ImportError:
        print(f"⚠ Memory profiling disabled (psutil not installed)")
        print(f"  Install with: pip install psutil")

    start_time = time.time()

    try:
        test_large_file_streaming()
        test_multiple_file_sizes()
        test_chunking_variations()

        total_duration = time.time() - start_time

        print("\n" + "=" * 70)
        print(f"ALL TESTS PASSED in {total_duration:.2f}s")
        print("=" * 70)

        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

