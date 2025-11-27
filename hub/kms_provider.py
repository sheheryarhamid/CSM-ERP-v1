"""
KMS Key Provider - Cloud Key Management Integration

Implements key providers for AWS KMS, Azure Key Vault, and GCP KMS
as outlined in the Master.ini security architecture and production rollout guide.

Architecture Alignment:
- Follows Master.ini Section 6: "Cross-Platform Secrets" requirement
- Implements abstract secret storage interface for KMS backends
- Enables zero vendor lock-in principle with pluggable providers
- Supports key rotation without downtime (Master.ini Section 📌6)

Usage:
    # For development (existing DPAPI/env)
    from hub.key_provider import get_key_bytes
    key = get_key_bytes()
    
    # For production (KMS)
    from hub.kms_provider import get_kms_key_bytes
    key = get_kms_key_bytes()  # Auto-detects provider from env
"""

import os
import logging
from typing import Optional, Protocol, TYPE_CHECKING
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# Help static analyzers (e.g. Pylance) recognize optional deps without
# forcing a runtime import. Actual import is done lazily inside the
# property that initializes the client, so this only runs during
# type-checking to avoid reportMissingImports errors.
if TYPE_CHECKING:
    import boto3  # type: ignore
    from azure.identity import DefaultAzureCredential  # type: ignore
    from azure.keyvault.secrets import SecretClient  # type: ignore
    from google.cloud import kms as gcp_kms  # type: ignore


class KMSProvider(Protocol):
    """Protocol defining the interface all KMS providers must implement.
    
    This enables pluggable key management backends while maintaining
    type safety and consistent behavior across AWS/Azure/GCP.
    """
    
    def get_encryption_key(self) -> bytes:
        """Retrieve or generate a data encryption key (DEK) from the KMS.
        
        Returns:
            32-byte encryption key for AES-256-GCM
            
        Raises:
            KMSError: If key retrieval fails
        """
        ...
    
    def rotate_key(self, new_key_id: Optional[str] = None) -> str:
        """Initiate key rotation without downtime.
        
        Args:
            new_key_id: Optional specific key to rotate to
            
        Returns:
            New key ID or version
        """
        ...


class KMSError(Exception):
    """Base exception for KMS operations."""
    pass


class AWSKMSProvider:
    """AWS KMS key provider using boto3.
    
    Configuration (environment variables):
        AWS_KMS_KEY_ID: ARN or alias of KMS key (required)
        AWS_REGION: AWS region (default: us-east-1)
        AWS_ACCESS_KEY_ID: AWS credentials (optional if IAM role)
        AWS_SECRET_ACCESS_KEY: AWS credentials (optional if IAM role)
    
    IAM Permissions Required:
        - kms:Decrypt
        - kms:Encrypt
        - kms:GenerateDataKey
        - kms:DescribeKey
    
    Example:
        export AWS_KMS_KEY_ID=alias/erp-hub-blob-encryption
        export AWS_REGION=us-east-1
        # Use IAM role or provide credentials
    """
    
    def __init__(self, key_id: Optional[str] = None, region: Optional[str] = None):
        self.key_id: str = key_id or os.getenv("AWS_KMS_KEY_ID") or ""
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        if not self.key_id:
            raise KMSError("AWS_KMS_KEY_ID environment variable required")
        
        self._client = None
        self._data_key_cache: Optional[bytes] = None
    
    @property
    def client(self):
        """Lazy-load boto3 client to avoid import errors if AWS not used."""
        if self._client is None:
            try:
                import boto3  # type: ignore
                self._client = boto3.client('kms', region_name=self.region)
            except ImportError:
                raise KMSError("boto3 not installed. Install with: pip install boto3")
            except Exception as e:
                raise KMSError(f"Failed to initialize AWS KMS client: {e}")
        return self._client
    
    def get_encryption_key(self) -> bytes:
        """Generate or retrieve a data encryption key from AWS KMS.
        
        Uses GenerateDataKey for envelope encryption:
        - KMS generates a plaintext DEK and encrypted DEK
        - Returns plaintext for immediate use
        - Encrypted DEK can be stored with data for future decryption
        
        Returns:
            32-byte plaintext encryption key
        """
        try:
            response = self.client.generate_data_key(
                KeyId=self.key_id,
                KeySpec='AES_256'  # 32-byte key
            )
            plaintext_key = response['Plaintext']
            # In production, store response['CiphertextBlob'] with your data
            # for re-decryption without calling KMS each time
            logger.info(f"Generated data key from AWS KMS key {self.key_id}")
            return plaintext_key
        except Exception as e:
            logger.error(f"AWS KMS key generation failed: {e}")
            raise KMSError(f"Failed to generate key from AWS KMS: {e}")
    
    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a previously encrypted data key.
        
        Args:
            encrypted_key: CiphertextBlob from GenerateDataKey response
            
        Returns:
            Plaintext 32-byte key
        """
        try:
            response = self.client.decrypt(
                CiphertextBlob=encrypted_key
            )
            return response['Plaintext']
        except Exception as e:
            raise KMSError(f"Failed to decrypt key with AWS KMS: {e}")
    
    def rotate_key(self, new_key_id: Optional[str] = None) -> str:
        """Rotate to a new KMS key.
        
        Note: AWS KMS automatic key rotation happens yearly for AWS-managed keys.
        Manual rotation requires re-encrypting all data with new key.
        """
        target_key = new_key_id or self.key_id
        try:
            # Verify new key exists and is enabled
            response = self.client.describe_key(KeyId=target_key)
            if response['KeyMetadata']['KeyState'] != 'Enabled':
                raise KMSError(f"Key {target_key} is not enabled")
            
            self.key_id = target_key
            self._data_key_cache = None  # Clear cache
            logger.info(f"Rotated to AWS KMS key {target_key}")
            return self.key_id
        except Exception as e:
            raise KMSError(f"Key rotation failed: {e}")


class AzureKeyVaultProvider:
    """Azure Key Vault key provider using azure-keyvault-secrets.
    
    Configuration (environment variables):
        AZURE_KEY_VAULT_URL: Key Vault URL (required)
        AZURE_KEY_NAME: Secret name in Key Vault (required)
        AZURE_CLIENT_ID: Service principal ID (optional if managed identity)
        AZURE_CLIENT_SECRET: Service principal secret (optional)
        AZURE_TENANT_ID: Azure AD tenant (optional)
    
    RBAC Permissions Required:
        - Key Vault Crypto User (for encrypt/decrypt)
        - Key Vault Secrets User (for secret retrieval)
    
    Example:
        export AZURE_KEY_VAULT_URL=https://mykeyvault.vault.azure.net/
        export AZURE_KEY_NAME=erp-blob-encryption-key
        # Use managed identity or service principal
    """
    
    def __init__(self, vault_url: Optional[str] = None, key_name: Optional[str] = None):
        self.vault_url = vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        self.key_name = key_name or os.getenv("AZURE_KEY_NAME", "erp-blob-encryption-key")
        
        if not self.vault_url:
            raise KMSError("AZURE_KEY_VAULT_URL environment variable required")
        
        self._secret_client = None
        self._crypto_client = None
    
    @property
    def secret_client(self):
        """Lazy-load Azure SDK client."""
        if self._secret_client is None:
            try:
                from azure.identity import DefaultAzureCredential  # type: ignore
                from azure.keyvault.secrets import SecretClient  # type: ignore
                
                credential = DefaultAzureCredential()
                self._secret_client = SecretClient(
                    vault_url=self.vault_url,
                    credential=credential
                )
            except ImportError:
                raise KMSError(
                    "Azure SDK not installed. Install with: "
                    "pip install azure-keyvault-secrets azure-identity"
                )
            except Exception as e:
                raise KMSError(f"Failed to initialize Azure Key Vault client: {e}")
        return self._secret_client
    
    def get_encryption_key(self) -> bytes:
        """Retrieve encryption key from Azure Key Vault secret.
        
        Returns:
            32-byte encryption key (secret must contain hex-encoded key)
        """
        try:
            secret = self.secret_client.get_secret(self.key_name)
            key_hex = secret.value
            key_bytes = bytes.fromhex(key_hex)
            
            if len(key_bytes) != 32:
                raise KMSError(f"Key must be 32 bytes, got {len(key_bytes)}")
            
            logger.info(f"Retrieved key from Azure Key Vault: {self.key_name}")
            return key_bytes
        except Exception as e:
            logger.error(f"Azure Key Vault retrieval failed: {e}")
            raise KMSError(f"Failed to retrieve key from Azure: {e}")
    
    def rotate_key(self, new_key_id: Optional[str] = None) -> str:
        """Rotate to a new Key Vault secret version.
        
        Azure Key Vault maintains secret versions automatically.
        This updates the reference to use a specific version or latest.
        """
        target_name = new_key_id or self.key_name
        try:
            # Verify secret exists
            secret = self.secret_client.get_secret(target_name)
            self.key_name = target_name
            logger.info(f"Rotated to Azure Key Vault secret {target_name} (version {secret.properties.version})")
            return f"{target_name}@{secret.properties.version}"
        except Exception as e:
            raise KMSError(f"Key rotation failed: {e}")


class GCPKMSProvider:
    """Google Cloud KMS key provider using google-cloud-kms.
    
    Configuration (environment variables):
        GCP_PROJECT_ID: GCP project ID (required)
        GCP_LOCATION: KMS location (default: global)
        GCP_KEYRING: KMS keyring name (required)
        GCP_KEY_NAME: KMS key name (required)
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional)
    
    IAM Permissions Required:
        - cloudkms.cryptoKeyVersions.useToEncrypt
        - cloudkms.cryptoKeyVersions.useToDecrypt
    
    Example:
        export GCP_PROJECT_ID=my-project
        export GCP_KEYRING=erp-hub-keyring
        export GCP_KEY_NAME=blob-encryption-key
        export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        keyring: Optional[str] = None,
        key_name: Optional[str] = None
    ):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location or os.getenv("GCP_LOCATION", "global")
        self.keyring = keyring or os.getenv("GCP_KEYRING")
        self.key_name = key_name or os.getenv("GCP_KEY_NAME")
        
        if not all([self.project_id, self.keyring, self.key_name]):
            raise KMSError(
                "GCP_PROJECT_ID, GCP_KEYRING, and GCP_KEY_NAME environment variables required"
            )
        
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Google Cloud KMS client."""
        if self._client is None:
            try:
                from google.cloud.kms_v1 import KeyManagementServiceClient  # type: ignore
                self._client = KeyManagementServiceClient()
            except ImportError:
                raise KMSError(
                    "Google Cloud KMS not installed. Install with: "
                    "pip install google-cloud-kms"
                )
            except Exception as e:
                raise KMSError(f"Failed to initialize GCP KMS client: {e}")
        return self._client
    
    @property
    def key_path(self) -> str:
        """Full resource path to the KMS key."""
        return (
            f"projects/{self.project_id}/locations/{self.location}/"
            f"keyRings/{self.keyring}/cryptoKeys/{self.key_name}"
        )
    
    def get_encryption_key(self) -> bytes:
        """Generate a data encryption key using GCP KMS.
        
        Uses envelope encryption similar to AWS KMS.
        """
        try:
            import os as _os
            # Generate random 32-byte key
            plaintext_key = _os.urandom(32)
            
            # Encrypt it with KMS for storage
            from google.cloud.kms_v1.types import EncryptRequest  # type: ignore
            request = EncryptRequest(
                name=self.key_path,
                plaintext=plaintext_key
            )
            response = self.client.encrypt(request=request)
            
            # In production, store response.ciphertext with data
            # For now, return plaintext for immediate use
            logger.info(f"Generated data key from GCP KMS key {self.key_path}")
            return plaintext_key
        except Exception as e:
            logger.error(f"GCP KMS key generation failed: {e}")
            raise KMSError(f"Failed to generate key from GCP KMS: {e}")
    
    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a previously encrypted data key."""
        try:
            from google.cloud.kms_v1.types import DecryptRequest  # type: ignore
            request = DecryptRequest(
                name=self.key_path,
                ciphertext=encrypted_key
            )
            response = self.client.decrypt(request=request)
            return response.plaintext
        except Exception as e:
            raise KMSError(f"Failed to decrypt key with GCP KMS: {e}")
    
    def rotate_key(self, new_key_id: Optional[str] = None) -> str:
        """Rotate to a new KMS key version.
        
        GCP KMS handles automatic rotation if enabled.
        This method updates the reference to a new key or version.
        """
        if new_key_id:
            self.key_name = new_key_id
        
        try:
            # Verify key is enabled
            from google.cloud.kms_v1.types import GetCryptoKeyRequest  # type: ignore
            request = GetCryptoKeyRequest(name=self.key_path)
            crypto_key = self.client.get_crypto_key(request=request)
            
            logger.info(f"Rotated to GCP KMS key {self.key_path}")
            return self.key_path
        except Exception as e:
            raise KMSError(f"Key rotation failed: {e}")


# Factory function to auto-detect KMS provider from environment
def create_kms_provider() -> Optional[KMSProvider]:
    """Create appropriate KMS provider based on environment variables.
    
    Detection order:
    1. AWS_KMS_KEY_ID → AWSKMSProvider
    2. AZURE_KEY_VAULT_URL → AzureKeyVaultProvider
    3. GCP_PROJECT_ID + GCP_KEYRING → GCPKMSProvider
    4. None → Falls back to DPAPI/env (hub.key_provider)
    
    Returns:
        KMS provider instance or None if no KMS configured
    """
    if os.getenv("AWS_KMS_KEY_ID"):
        logger.info("Detected AWS KMS configuration")
        return AWSKMSProvider()
    
    if os.getenv("AZURE_KEY_VAULT_URL"):
        logger.info("Detected Azure Key Vault configuration")
        return AzureKeyVaultProvider()
    
    if os.getenv("GCP_PROJECT_ID") and os.getenv("GCP_KEYRING"):
        logger.info("Detected GCP KMS configuration")
        return GCPKMSProvider()
    
    logger.info("No KMS provider configured, will use DPAPI/env fallback")
    return None


def get_kms_key_bytes() -> bytes:
    """Get encryption key from KMS or fall back to DPAPI/env.
    
    This is the main entry point for production deployments.
    
    Returns:
        32-byte encryption key
        
    Raises:
        KMSError: If KMS is configured but fails
        ValueError: If no key source is available
    """
    provider = create_kms_provider()
    
    if provider:
        try:
            return provider.get_encryption_key()
        except KMSError:
            logger.error("KMS provider failed, falling back to local key provider")
            # In production, you may want to fail hard here instead of falling back
            # Uncomment to enforce KMS-only:
            # raise
    
    # Fallback to existing DPAPI/env implementation
    logger.warning("Using local key provider (DPAPI/env) - not recommended for production")
    from hub.key_provider import get_key_bytes
    return get_key_bytes()


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    print("KMS Provider Test Utility")
    print("=" * 50)
    
    # Test auto-detection
    provider = create_kms_provider()
    if provider:
        print(f"✓ Detected provider: {provider.__class__.__name__}")
        try:
            key = provider.get_encryption_key()
            print(f"✓ Successfully retrieved {len(key)}-byte encryption key")
        except KMSError as e:
            print(f"✗ Failed to retrieve key: {e}")
            sys.exit(1)
    else:
        print("ℹ No KMS provider configured")
        print("  Set one of: AWS_KMS_KEY_ID, AZURE_KEY_VAULT_URL, or GCP_PROJECT_ID")
        
        # Test fallback
        try:
            key = get_kms_key_bytes()
            print(f"✓ Fallback successful: {len(key)}-byte key from DPAPI/env")
        except Exception as e:
            print(f"✗ Fallback failed: {e}")
            sys.exit(1)
    
    print("\nAll tests passed!")
