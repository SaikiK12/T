"""Ephemeral offline PKI signing invented test bytes, never trading credentials."""
from pathlib import Path
import tempfile
from lab.m090_capture import openssl,sha


class Authority:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test_m090_pki_")
        self.path = p = Path(self.temp.name)
        for n,raw in dict(index="",serial="1000\n",crlnumber="1000\n",tsserial="1000\n").items():
            (p/n).write_text(raw)
        self.config = f"""[ca]
default_ca = issuer
[issuer]
database = {p}/index
new_certs_dir = {p}
certificate = {p}/root.pem
private_key = {p}/root.key
serial = {p}/serial
crlnumber = {p}/crlnumber
default_md = sha256
default_days = 2
default_crl_days = 1
policy = names
x509_extensions = timestamp
[names]
commonName = supplied
[timestamp]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,timeStamping
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
[tsa]
default_tsa = service
[service]
serial = {p}/tsserial
signer_cert = {p}/signer.pem
certs = {p}/root.pem
signer_key = {p}/signer.key
signer_digest = sha256
default_policy = 1.2.3.4.5
digests = sha256
clock_precision_digits = 0
ordering = yes
tsa_name = yes
ess_cert_id_chain = no
ess_cert_id_alg = sha256
"""
        (p/"config").write_text(self.config)
        openssl(["req","-new","-x509","-newkey","ec","-pkeyopt","ec_paramgen_curve:P-256","-nodes",
                 "-keyout",p/"root.key","-out",p/"root.pem","-subj","/CN=Offline test root","-days","3",
                 "-addext","basicConstraints=critical,CA:true","-addext","keyUsage=critical,keyCertSign,cRLSign"])
        openssl(["req","-new","-newkey","ec","-pkeyopt","ec_paramgen_curve:P-256","-nodes",
                 "-keyout",p/"signer.key","-out",p/"signer.csr","-subj","/CN=Offline test TSA"])
        openssl(["ca","-batch","-config",p/"config","-in",p/"signer.csr","-out",p/"signer.pem"])
        openssl(["ca","-gencrl","-config",p/"config","-out",p/"crl.pem"])
        self.trust = dict(root=(p/"root.pem").read_bytes(),chain=(p/"root.pem").read_bytes(),
                          crls=(p/"crl.pem").read_bytes(),policy="1.2.3.4.5",
                          signer_sha256=sha(openssl(["x509","-in",p/"signer.pem","-outform","DER"])),
                          crl_urls=["https://test.invalid/a","https://test.invalid/b"],url="http://timestamp.digicert.com")

    def close(self):
        self.temp.cleanup()

    def sign(self,q,accuracy=False):
        p = self.path
        (p/"q").write_bytes(q)
        (p/"config").write_text(self.config+("accuracy = secs:1\n" if accuracy else ""))
        openssl(["ts","-reply","-config",p/"config","-queryfile",p/"q","-out",p/"reply"])
        return (p/"reply").read_bytes()
