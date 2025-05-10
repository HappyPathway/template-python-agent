#!/usr/bin/env python3
"""Storage Usage Example.

This example script demonstrates the usage of different storage implementations
and how to extend them for custom functionality.
"""

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Dict, Any, Optional

from ailf.core.storage import StorageBase  # Changed from ailf.core.storage_base
from ailf.core.local_storage import LocalStorage
from ailf.core.cached_storage import CachedLocalStorage

# Uncomment to use GCS storage (requires google-cloud-storage package)
# from ailf.cloud.gcs_storage import GCSStorage


class CustomEncryptedStorage(LocalStorage):
    """Example of a custom storage implementation with encryption.
    
    This class extends LocalStorage and implements a basic encryption scheme
    for sensitive data.
    """
    
    def __init__(self, base_path=None, config=None, encryption_key=None):
        """Initialize with custom encryption key."""
        self.encryption_key = encryption_key or os.environ.get("ENCRYPTION_KEY", "default-key")
        super().__init__(base_path, config)
        
    def _get_default_config(self):
        """Override default config to enable encryption."""
        config = super()._get_default_config()
        config["encrypt"] = True
        return config
        
    def _encrypt_data(self, data: Dict) -> Dict:
        """Implement a (very) simple encryption scheme.
        
        Note: This is for demonstration purposes only and is NOT secure.
        In a real implementation, use a proper encryption library.
        """
        if not isinstance(data, dict):
            return data
            
        # In a real implementation, we would use proper encryption here
        # This is just a simple XOR example that is NOT secure
        serialized = json.dumps(data)
        encrypted_chars = []
        
        for i, char in enumerate(serialized):
            # Simple XOR with repeating key
            key_char = self.encryption_key[i % len(self.encryption_key)]
            encrypted_char = chr(ord(char) ^ ord(key_char))
            encrypted_chars.append(encrypted_char)
            
        encrypted_text = ''.join(encrypted_chars)
        return {
            "__encrypted_v1": True,  # Version marker
            "data": encrypted_text
        }
        
    def _decrypt_data(self, data: Dict) -> Dict:
        """Decrypt data using the simple encryption scheme."""
        if not isinstance(data, dict) or not data.get("__encrypted_v1"):
            return data
            
        encrypted_text = data.get("data", "")
        decrypted_chars = []
        
        for i, char in enumerate(encrypted_text):
            # Simple XOR with repeating key (reverse of encryption)
            key_char = self.encryption_key[i % len(self.encryption_key)]
            decrypted_char = chr(ord(char) ^ ord(key_char))
            decrypted_chars.append(decrypted_char)
            
        decrypted_text = ''.join(decrypted_chars)
        
        try:
            return json.loads(decrypted_text)
        except json.JSONDecodeError:
            print("Error: Decryption failed. Incorrect key?")
            return {}


def storage_benchmark(storage: StorageBase, num_operations: int = 100) -> Dict[str, Any]:
    """Benchmark storage operations.
    
    Args:
        storage: Storage instance to benchmark
        num_operations: Number of operations to perform
        
    Returns:
        Dict[str, Any]: Benchmark results
    """
    results = {
        "save_time": 0,
        "get_time": 0, 
        "delete_time": 0,
        "operations": num_operations
    }
    
    # Test data
    test_data = {"key": "value", "nested": {"data": [1, 2, 3, 4, 5]}}
    
    # Benchmark save operations
    start_time = time.time()
    for i in range(num_operations):
        path = f"benchmark/item_{i}.json"
        storage.save_json(test_data, path)
    results["save_time"] = time.time() - start_time
    
    # Benchmark get operations
    start_time = time.time()
    for i in range(num_operations):
        path = f"benchmark/item_{i}.json"
        data = storage.get_json(path)
        assert data["key"] == "value"  # Verify data integrity
    results["get_time"] = time.time() - start_time
    
    # Benchmark delete operations
    start_time = time.time()
    for i in range(num_operations):
        path = f"benchmark/item_{i}.json"
        storage.delete(path)
    results["delete_time"] = time.time() - start_time
    
    return results


def main():
    """Run the storage examples."""
    print("Storage Implementation Examples\n" + "="*30)
    
    # Create a temporary directory for test data
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # Example 1: Basic LocalStorage usage
        print("\n1. Basic LocalStorage Usage")
        print("--------------------------")
        local_storage = LocalStorage(base_path / "local")
        
        # Save some data
        config_path = local_storage.save_json(
            {"app_name": "Example App", "version": "1.0.0"}, 
            "config/app_config.json"
        )
        print(f"Saved config to: {config_path}")
        
        # Read the data back
        config_data = local_storage.get_json("config/app_config.json")
        print(f"Read config data: {config_data}")
        
        # List files
        files = local_storage.list_directory("config")
        print(f"Files in config directory: {files}")
        
        # Check if a file exists
        exists = local_storage.exists("config/app_config.json")
        print(f"Config file exists: {exists}")
        
        # Example 2: CachedLocalStorage with performance benefits
        print("\n2. CachedLocalStorage Usage")
        print("-------------------------")
        cached_storage = CachedLocalStorage(
            base_path / "cached",
            config={"max_cache_size": 50, "cache_ttl": 60}
        )
        
        # Save data
        user_path = cached_storage.save_json(
            {"id": "user123", "name": "Test User"}, 
            "users/user123.json"
        )
        print(f"Saved user data to: {user_path}")
        
        # First read (from disk)
        start_time = time.time()
        user_data = cached_storage.get_json("users/user123.json")
        first_read_time = time.time() - start_time
        print(f"First read (from disk): {first_read_time:.6f} seconds")
        
        # Second read (from cache)
        start_time = time.time()
        user_data = cached_storage.get_json("users/user123.json")
        second_read_time = time.time() - start_time
        print(f"Second read (from cache): {second_read_time:.6f} seconds")
        print(f"Cache speedup: {first_read_time / second_read_time:.2f}x")
        
        # Get cache statistics
        cache_stats = cached_storage.get_cache_stats()
        print(f"Cache statistics: {cache_stats}")
        
        # Example 3: Custom EncryptedStorage
        print("\n3. Custom EncryptedStorage Usage")
        print("------------------------------")
        encrypted_storage = CustomEncryptedStorage(
            base_path / "encrypted",
            encryption_key="SECRET-KEY-12345"
        )
        
        # Save sensitive data
        secret_path = encrypted_storage.save_json(
            {"api_key": "sk_live_1234567890abcdef", "secret": "very-secret-value"}, 
            "secrets/api_keys.json"
        )
        print(f"Saved encrypted data to: {secret_path}")
        
        # Read back the data (decryption happens automatically)
        secret_data = encrypted_storage.get_json("secrets/api_keys.json")
        print(f"Decrypted data: {secret_data}")
        
        # Show the raw encrypted file content
        with open(Path(base_path) / "encrypted/secrets/api_keys.json", "r") as f:
            raw_content = f.read()
            print(f"Raw encrypted content: {raw_content[:60]}...")
        
        # Example 4: Storage performance benchmark
        print("\n4. Storage Performance Benchmark")
        print("-----------------------------")
        
        num_operations = 10  # Small number for example purposes
        
        # Benchmark LocalStorage
        print("Benchmarking LocalStorage...")
        local_results = storage_benchmark(
            LocalStorage(base_path / "bench_local"),
            num_operations
        )
        
        # Benchmark CachedLocalStorage
        print("Benchmarking CachedLocalStorage...")
        cached_results = storage_benchmark(
            CachedLocalStorage(base_path / "bench_cached"),
            num_operations
        )
        
        # Print benchmark results
        print("\nBenchmark Results (seconds):")
        print(f"{'Operation':<10} {'LocalStorage':<15} {'CachedStorage':<15} {'Speedup':<10}")
        print("-" * 50)
        
        for op in ["save_time", "get_time", "delete_time"]:
            local_time = local_results[op]
            cached_time = cached_results[op]
            speedup = local_time / cached_time if cached_time > 0 else 1.0
            
            print(f"{op.split('_')[0]:<10} {local_time:<15.6f} {cached_time:<15.6f} {speedup:<10.2f}x")
        
        # Example 5: GCS Storage (commented out by default)
        """
        # Uncomment below to try GCS storage (requires google-cloud-storage package and GCP setup)
        print("\n5. GCS Storage (Google Cloud Storage)")
        print("----------------------------------")
        
        # Replace with your bucket name
        bucket_name = "my-example-bucket"
        
        # Create GCS storage instance
        gcs_storage = GCSStorage(bucket_name, prefix="example")
        
        # Save data to GCS
        gcs_path = gcs_storage.save_json(
            {"timestamp": time.time(), "source": "example-script"},
            "test/example.json"
        )
        print(f"Saved data to GCS: {gcs_path}")
        
        # Read data back
        gcs_data = gcs_storage.get_json("test/example.json")
        print(f"Read data from GCS: {gcs_data}")
        
        # Check if file exists in GCS
        gcs_exists = gcs_storage.exists("test/example.json") 
        print(f"File exists in GCS: {gcs_exists}")
        """


if __name__ == "__main__":
    main()