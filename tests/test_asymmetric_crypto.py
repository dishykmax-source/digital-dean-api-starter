import pytest
from app.security.asymmetric import CONTEXT, PROFILES, DecryptionError, decrypt, encrypt, generate_keypair, oaep_max_bytes

@pytest.mark.parametrize('profile', list(PROFILES))
def test_roundtrip(profile):
    key=generate_keypair(profile); size=64 if PROFILES[profile].kind=='direct' else 1024
    data=b'a'*size; env=encrypt(profile,key.public_key(),data)
    assert decrypt(profile,key,env)==data

@pytest.mark.parametrize('profile', list(PROFILES))
def test_tamper_and_context(profile):
    key=generate_keypair(profile); env=encrypt(profile,key.public_key(),b'hello')
    damaged=env[:-1]+bytes([env[-1]^1])
    with pytest.raises(DecryptionError): decrypt(profile,key,damaged)
    with pytest.raises(DecryptionError): decrypt(profile,key,env,CONTEXT+b'bad')

@pytest.mark.parametrize('bits,maximum',[(2048,190),(3072,318)])
def test_oaep_boundary(bits,maximum):
    profile='rsa2048-oaep' if bits==2048 else 'rsa3072-oaep'; key=generate_keypair(profile)
    assert len(decrypt(profile,key,encrypt(profile,key.public_key(),b'x'*maximum)))==maximum
    with pytest.raises(ValueError): encrypt(profile,key.public_key(),b'x'*(maximum+1))
    assert oaep_max_bytes(bits)==maximum
