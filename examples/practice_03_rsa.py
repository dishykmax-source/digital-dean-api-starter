from app.security.asymmetric import encrypt, decrypt, generate_keypair

if __name__ == '__main__':
    private=generate_keypair('rsa2048-oaep'); message=b'digital-dean:practice-03'
    envelope=encrypt('rsa2048-oaep',private.public_key(),message)
    assert decrypt('rsa2048-oaep',private,envelope)==message
    print(f'RSA-OAEP roundtrip OK; ciphertext={len(envelope)} bytes')
