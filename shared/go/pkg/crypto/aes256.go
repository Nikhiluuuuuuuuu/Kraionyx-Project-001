// Package crypto provides AES-256-GCM encryption and decryption utilities
// for securing sensitive medical data in transit and at rest.
package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"sync"
)

const (
	// KeySize is the required key length for AES-256: 32 bytes.
	KeySize = 32
	// NonceSize is the standard GCM nonce length: 12 bytes.
	NonceSize = 12
)

var (
	// ErrInvalidKeySize is returned when the provided key is not 32 bytes.
	ErrInvalidKeySize = errors.New("crypto: key must be exactly 32 bytes for AES-256")
	// ErrCiphertextTooShort is returned when the ciphertext is shorter than the nonce.
	ErrCiphertextTooShort = errors.New("crypto: ciphertext too short, must include nonce prefix")
	// ErrDecryptionFailed is returned when GCM authentication or decryption fails.
	ErrDecryptionFailed = errors.New("crypto: decryption failed, data may be corrupted or key is wrong")
)

// Encrypt encrypts plaintext using AES-256-GCM with the provided 32-byte key.
// It returns a base64-encoded string containing the 12-byte nonce prepended to
// the ciphertext and authentication tag. A unique random nonce is generated for
// each call, making it safe to reuse the same key across multiple encryptions.
var gcmCache sync.Map

func getGCM(key []byte) (cipher.AEAD, error) {
	if len(key) != KeySize {
		return nil, ErrInvalidKeySize
	}
	keyStr := string(key)
	if cached, ok := gcmCache.Load(keyStr); ok {
		return cached.(cipher.AEAD), nil
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to create AES cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to create GCM: %w", err)
	}

	gcmCache.Store(keyStr, gcm)
	return gcm, nil
}

func Encrypt(plaintext []byte, key []byte) (string, error) {
	gcm, err := getGCM(key)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, NonceSize)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("crypto: failed to generate nonce: %w", err)
	}

	sealed := gcm.Seal(nonce, nonce, plaintext, nil)
	return base64.StdEncoding.EncodeToString(sealed), nil
}

// Decrypt decodes a base64-encoded string produced by Encrypt and decrypts the
// ciphertext using AES-256-GCM with the provided 32-byte key. It extracts the
// 12-byte nonce from the beginning of the decoded data and returns the original
// plaintext.
func Decrypt(encoded string, key []byte) ([]byte, error) {
	data, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to decode base64: %w", err)
	}

	if len(data) < NonceSize {
		return nil, ErrCiphertextTooShort
	}

	gcm, err := getGCM(key)
	if err != nil {
		return nil, err
	}

	nonce := data[:NonceSize]
	ciphertext := data[NonceSize:]

	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, ErrDecryptionFailed
	}

	return plaintext, nil
}

// GenerateKey generates a cryptographically secure random 32-byte key suitable
// for use with AES-256 encryption.
func GenerateKey() ([]byte, error) {
	key := make([]byte, KeySize)
	if _, err := io.ReadFull(rand.Reader, key); err != nil {
		return nil, fmt.Errorf("crypto: failed to generate key: %w", err)
	}
	return key, nil
}

// KeyFromBase64 decodes a base64-encoded string into a 32-byte AES-256 key.
// It returns an error if the decoded key is not exactly 32 bytes.
func KeyFromBase64(encoded string) ([]byte, error) {
	key, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to decode base64 key: %w", err)
	}
	if len(key) != KeySize {
		return nil, fmt.Errorf("crypto: decoded key is %d bytes, expected %d", len(key), KeySize)
	}
	return key, nil
}
