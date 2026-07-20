# ImgChain — Image Recognition + Blockchain Prototype

MVP for the *Rapid Systems Integration* course project. Integrates two
technologies from the course list: **AI (image recognition)** and
**Blockchain**.

## 1. What the system does

A user uploads an image through a web UI. The system:

1. **Fingerprints** the raw image bytes with SHA-256.
2. **Classifies** the image with a CNN (pretrained ResNet18 / ImageNet).
3. **Mines a block** containing the fingerprint, the classification result,
   a link to the previous block's hash, and a proof-of-work nonce.
4. Lets anyone **re-verify** the whole chain on demand — if any stored
   block is altered after the fact, verification fails and identifies
   exactly which block broke.

This models a real use case: proving *what* an image was and *what the
system concluded about it* at a specific point in time, in a way that
can't be silently edited later — e.g. chain-of-custody for evidence
photos, provenance for AI-labeled training data, or audit trails for
automated content moderation decisions.

## 2. Components implemented

| Component | File | Status |
|---|---|---|
| Image hashing (SHA-256) | `image_recognition.py` | ✅ Done |
| CNN classification (ResNet18/ImageNet) | `image_recognition.py` | ✅ Done (requires one-time weight download) |
| Offline fallback classifier | `image_recognition.py` | ✅ Done — keeps the pipeline runnable with no internet access |
| Custom blockchain (blocks, linking, proof-of-work mining) | `blockchain.py` | ✅ Done |
| Chain integrity verification | `blockchain.py` | ✅ Done, tamper-tested |
| Duplicate-image detection | `app.py` | ✅ Done |
| Web UI (upload, per-block result, full ledger view) | `app.py`, `templates/` | ✅ Done |
| Persistence | `blockchain.py` | ✅ JSON file (`data/chain.json`) |

### How image recognition works here
`image_recognition.py` loads a ResNet18 CNN pretrained on ImageNet via
torchvision. An uploaded image is resized/normalized by the model's own
preprocessing transform, run through the network, and the highest-probability
class from the 1,000 ImageNet categories is returned with its confidence
score. If torch/torchvision aren't installed or the pretrained weights can't
be downloaded (no internet), the module automatically falls back to a
deterministic color-histogram heuristic and clearly labels the result
`[FALLBACK]` so it's never mistaken for a real classification. This is what
ran during local testing of this prototype, since the sandbox it was built
in has no internet access — the ResNet18 path is implemented and correct,
but untested against live downloaded weights, which is the first thing to
confirm in an environment with normal internet access.

### How blockchain is used here
`blockchain.py` implements a small custom chain, not a public/cryptocurrency
chain. Each block stores the image hash, filename, prediction, confidence,
and the hash of the previous block. Blocks are "mined" with a simple
proof-of-work (find a nonce that makes the block's hash start with two
zeros) purely to demonstrate the concept cheaply. `is_valid()` recomputes
every block's hash and checks the links; changing anything in a stored
block — even the prediction — breaks the chain from that point forward,
which was confirmed with a tamper test during development. Blockchain is
serving three roles simultaneously: **data security** (any edit is
detectable), **verification** (independent recomputation, not trust),
and **tracking** (an ordered, timestamped audit trail of every image
processed).

## 3. What's still missing / next steps

This is an MVP, not the finished system. Gaps to close before final
submission:

- **Single-node only.** There's no peer-to-peer network or consensus —
  the "chain" lives in one JSON file. A real blockchain integration needs
  multiple nodes agreeing on chain state (or, more realistically for a
  3-week project, anchoring block hashes to an existing testnet like
  Ethereum Sepolia via a smart contract, rather than building consensus
  from scratch).
- **No image storage strategy beyond local disk.** Images should move to
  content-addressed storage (e.g. IPFS) so the hash *is* the retrieval
  key, which is the more standard pattern for this kind of system.
- **CNN not validated against real downloaded weights yet** in this
  environment — needs to be run and confirmed once there's internet access.
- **No authentication/authorization** on uploads — anyone can add a block.
- **No automated test suite.** Testing so far was manual (see Section 4);
  this needs to become a proper `pytest` suite for the V&V report.
- **No fine-tuning.** ResNet18/ImageNet is a generic 1,000-class model,
  not adapted to any specific domain the project might target.
- **No deployment.** Currently runs only via Flask's development server.

## 4. Manual verification performed so far

- Byte-compiled all three Python modules — no syntax errors.
- Ran the recognition + blockchain pipeline end-to-end on two synthetic
  test images: hashing, classification (fallback mode), block mining, and
  chain validation all produced correct results.
- **Tamper test:** manually edited a stored block's `prediction` field
  after mining and re-ran `is_valid()` — correctly detected and reported
  which block was compromised.
- Exercised all four Flask routes (`/`, `/upload`, `/chain`, `/verify`)
  through Flask's test client, including the duplicate-image path.

This is the starting point for the formal **V&V Report** deliverable —
it needs documented edge cases (corrupt file upload, non-image file,
empty file, chain-length-zero, concurrent uploads) and should move from
manual script checks to automated tests.

## 5. Mapping to course deliverables

- **Scope Lock:** this README's Section 2/3 split (done vs. not-done) is
  a reasonable starting draft — needs the team's sign-off and instructor
  approval by end of Week 1.
- **Architecture Diagram:** draw the flow `Browser → Flask (/upload) →
  image_recognition.recognize() → blockchain.add_block() → JSON ledger →
  Browser (/chain)`, with the CNN and the mining step called out as the
  two integrated technologies.
- **Functional Prototype:** this repo + a short demo video walking
  through an upload, viewing the resulting block, and a verify call.
- **V&V Report:** expand Section 4 above into a full report with a test
  case table.
- **Final Reflection:** the offline-fallback design and the "single node,
  not a real network" limitation are good honest material for the
  integration-challenges discussion.

## 6. Running it

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

The first classification request will attempt to download ResNet18's
pretrained weights (~45MB); after that they're cached locally by torch.
