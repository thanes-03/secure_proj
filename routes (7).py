import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature


def generate_nonce() -> bytes:
    return os.urandom(12)


def aes_encrypt(key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
    """AES-256-GCM encrypt with an explicit nonce. Caller stores the nonce
    separately (e.g. notes.nonce, note_keys.key_nonce) — not prepended here."""
    return AESGCM(key).encrypt(nonce, plaintext, None)


def aes_decrypt(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """AES-256-GCM decrypt with an explicit nonce supplied by the caller."""
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def aes_encrypt_sealed(key: bytes, plaintext: bytes) -> bytes:
    """AES-256-GCM encrypt for blobs with no dedicated nonce column
    (e.g. users.rsa_private_key_encrypted). Returns nonce(12) + ciphertext + tag."""
    nonce = generate_nonce()
    return nonce + aes_encrypt(key, nonce, plaintext)


def aes_decrypt_sealed(key: bytes, blob: bytes) -> bytes:
    """Decrypt a blob produced by aes_encrypt_sealed (nonce prepended)."""
    return aes_decrypt(key, blob[:12], blob[12:])


def derive_vault_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit vault key from password using PBKDF2-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(password.encode())


def generate_note_key() -> bytes:
    return os.urandom(32)


def wrap_key_with_vault(vault_key: bytes, note_key: bytes) -> tuple[bytes, bytes]:
    """AES-encrypt note_key with vault_key. Returns (key_nonce, ciphertext)
    for storage in note_keys.key_nonce / note_keys.encrypted_note_key."""
    nonce = generate_nonce()
    return nonce, aes_encrypt(vault_key, nonce, note_key)


def unwrap_key_with_vault(vault_key: bytes, key_nonce: bytes, wrapped: bytes) -> bytes:
    """Decrypt a vault-wrapped note key using its stored key_nonce."""
    return aes_decrypt(vault_key, key_nonce, wrapped)


def generate_rsa_keypair() -> tuple[bytes, bytes]:
    """Generate RSA-2048 keypair. Returns (private_pem, public_pem)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def rsa_encrypt_key(public_pem: bytes, note_key: bytes) -> bytes:
    """RSA-OAEP encrypt note_key with recipient's public key."""
    pub = serialization.load_pem_public_key(public_pem)
    return pub.encrypt(note_key, padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ))


def rsa_decrypt_key(private_pem: bytes, encrypted_key: bytes) -> bytes:
    """RSA-OAEP decrypt note_key with private key."""
    priv = serialization.load_pem_private_key(private_pem, password=None)
    return priv.decrypt(encrypted_key, padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ))


def rsa_sign(private_pem: bytes, message: bytes) -> bytes:
    """RSA-PSS/SHA-256 sign a message with a PEM private key."""
    priv = serialization.load_pem_private_key(private_pem, password=None)
    return priv.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )


def rsa_verify(public_pem: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an RSA-PSS/SHA-256 signature. Returns False on any failure."""
    pub = serialization.load_pem_public_key(public_pem)
    try:
        pub.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
