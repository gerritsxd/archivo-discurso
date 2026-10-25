# GPU on demand for the transcription backlog and the 2023 backfill

*Researched 2026-10-25. Nothing here was run, no account was created, no money was spent. Prices come from provider pages fetched today unless marked "3rd party" (aggregators, undated or older) or "inferred". Provider pages change daily and several marketplaces (Vast, TensorDock, RunPod community) price per host, so re-check the live price before launching.*

## 0. First, an honest sizing check

Our local numbers: Whisper 10.6x, pyannote ~30x, run one after the other per item, so about **7.5x combined** on the 3060 Ti (1 / (1/10 + 1/30)).

| Job | Audio | Local 3060 Ti time |
|---|---|---|
| Today's backlog | 55 h | ~7.3 h (one evening) |
| Campaign day (15–25 h) | 20 h | ~2.7 h per day |
| 2023 backfill (several thousand h) | 3,000 h | ~400 h = 17 days non-stop |
| | 5,000 h | ~670 h = 28 days non-stop |

So **the PC already covers the backlog and the campaign.** A rented GPU is for the 2023 backfill (and for a debate-night peak). Bandwidth, not GPU, may become the real limit: 5,000 h as 16 kHz wav is about 575 GB; as Opus 32 kbps about 70 GB (see section 3).

## 1. Providers

| Provider | Suitable GPU | Price/h (Oct 2026) | EU | Billing | Egress / storage | Scripting | Verdict |
|---|---|---|---|---|---|---|---|
| **RunPod** pods | RTX 4090 24 GB | $0.89 listed; $0.34 "Community" in the page's structured data (unclear which tier is which) | "30+ regions", none named on the page | per second (page toggle; increments not stated) | egress not mentioned on pricing page; network volume $0.07/GB-mo; container disk $0.10/GB-mo; idle volume $0.20/GB-mo | REST API + `runpodctl`; pods can be removed from inside | **best fit** |
| | L4 24 GB | $0.59 (community $0.44) | | | | | |
| | A40 48 GB | $0.59 (community $0.35) | | | | | |
| | L40S 48 GB | $1.09 (community $0.79) | | | | | |
| | A100 80 GB | $1.79 PCIe/SXM (community $1.19–1.39) | | | | | |
| RunPod serverless | 4090 / L4 / A40 / L40S / A100 | $1.10 / $0.69 / $1.22 / $1.75 / $2.72 flex-rate per h | as above | per second, only while a job runs | | endpoint API | pricier per hour, but zero idle; overkill for a batch job |
| **Vast.ai** | RTX 4090 | marketplace, mostly $0.15–0.80; ~$0.31 on-demand (3rd party, Aug 2026); interruptible ~$0.15 | many hosts in EU, filterable | per second, no minimum (official) | set per host (bandwidth is billed on some hosts, check the listing) | `vastai` CLI + REST, very scriptable | cheapest, but variable host quality, some unreliable |
| | L4/A40/L40S/A100 | not on the fetched page (live grid only) | | | | | |
| **Modal** | L4 / A10 / L40S / A100 40 / A100 80 | $0.80 / $1.10 / $1.95 / $2.10 / $2.50 (derived from per-second rates) | region pinning costs 1.15–1.75x | per second, scale to zero | $0.04/GiB beyond 1 TiB/mo (Starter) | Python SDK, nicest DX; images defined in code | $30/month free credit on Starter would pay for ~1,000 h at L40S speed; no 4090 |
| **Lambda** | A10 24 GB | $1.29 | not stated on page | not stated (historically per minute) | not stated | API + CLI | no L4/4090/L40S on page; A100 40 GB $1.99, A100 80 GB $2.79, A6000 $1.09; poor value here |
| **TensorDock** | RTX 4090 | $0.27–0.46 "from" (3rd party, 2026; official page 404 today) | no EU-specific data found | per hour-ish marketplace, 20 % host commission | not found | API | skip unless Vast/RunPod fail |
| **Hetzner** GEX45 | RTX PRO 4000 Blackwell SFF 24 GB | €0.3429/h hourly, **€214/mo, setup fee €209** (official) | Helsinki | hourly or monthly, min term not stated | unlimited free traffic (official) | Robot API (dedicated server, provisioning takes minutes to hours) | EU, cheap per hour, but the setup fee kills ephemeral use; fine as a one-month rental for a huge backfill |
| Hetzner GEX131 | RTX PRO 6000 Blackwell 96 GB | from €1,499/mo, €1,499 setup, €2.40/h | Helsinki, Falkenstein | | | | overkill |
| **Scaleway** | L4 24 GB | €0.79/h (PAR-1); 2/4/8x L4 €1.58/3.15/6.30 | Paris | page does not say (assume per hour/minute) | not stated; 2.5 Gbps cap | Instance API/CLI, real VMs | EU-sovereign, 2-3x pricier per audio hour than 4090 pods; L40S only in PAR-2 (no price fetched) |
| **OVHcloud** | L40S 48 GB | $1.80/h (official marketing page, USD); €1.40/h at launch (3rd party, older) | GRA/other EU | hourly (3rd-party listings) | public-cloud traffic fees not retrieved | OpenStack API/CLI, you already have an OVH account | good EU option; **GPU quota usually needs a ticket for new projects (unverified)** |
| | L4 24 GB | $1.00/h (official marketing page); €0.75 at launch | | | | | |

Not verified (could not read the live page): Vast per-GPU grid, Scaleway/OVH egress, Lambda regions and granularity, exact RunPod EU datacentres. RunPod pricing page text said nothing addressed to an AI; no prompt-injection found in any fetched page.

## 2. Throughput and cost for our stack

### Speed per GPU (estimates, show your work)

Sources:
- faster-whisper README (large-v2, 13-min clip, RTX 3070 Ti 8 GB, fp16, beam 5): sequential 1m03s, **`batch_size=8` 17 s = 3.7x faster**, VRAM 4.5 GB to 6.1 GB. (large-v3 not tabulated; same architecture size.)
- RTX 4090, faster-whisper large-v3: ~70x fp16 (3rd party FAQ, batching unclear); a GPU-vendor blog reports 78x at batch 4 and 118x at batch 16 for a WhisperX pipeline (3rd party, marketing).
- pyannote community-1 official: 31 s per hour of audio on an H100 (about 116x); a third-party Rust port reports pyannote community-1 at 32x on an RTX 4090.
- Modal: batching gave ~2.8x on an A10G with Transformers.

My model: Whisper sequential ~22x on a 4090 (2x our 3060 Ti), batched ~60x (3.7x gain, below the vendor claims). Pyannote ~40x on a 4090 as-is. Sequential per item: 1/(1/22 + 1/40) = 14x. Batched Whisper + pyannote one after the other: 1/(1/60 + 1/40) = **24x**. **pyannote then dominates**, so running diarization of item N while Whisper does item N+1 (two processes, VRAM is plentiful at 24 GB) should push this towards ~35x; not assumed below.

| GPU | assumed combined speed (batched) | basis |
|---|---|---|
| RTX 4090 | **25x** (14x with today's sequential `src/process.py`) | above |
| L40S | 28x | similar silicon to 4090, more memory (inferred) |
| A100 80 GB | 35x | higher bandwidth (inferred) |
| L4 | 9x | ~1/3 of a 4090 (inferred; memory bandwidth 300 GB/s) |
| Hetzner RTX PRO 4000 | 15x | inferred, 24 GB, lower-end |

**Treat all of these as +/-40 %. Measure with one real hour on a rented box (~$0.50) before committing a big job.** The batched Whisper path also changes output slightly; re-run the m1 WER test with `m3/gpu_runner/transcribe_batched.py` first.

Overhead per run: boot + image pull + model load + audio transfer assumed **0.3 h** (1 h total for the 5,000 h case, which needs several runs or restarts). Ranges use the low/high price of the row.

### Cost (USD unless marked EUR), compute + overhead, excluding VAT and storage

| Setup | 100 h | 1,000 h | 5,000 h |
|---|---|---|---|
| RunPod/Vast 4090, batched 25x ($0.31–0.89/h) | $1.3–3.8 | $12.5–36 | $62–179 |
| RunPod 4090, as-is sequential 14x | $2.2–6.4 | $22–64 | $110–320 |
| RunPod L40S batched 28x ($0.79–1.09/h) | $3–4 | $29–40 | $142–196 |
| RunPod A100 80 GB 35x ($1.19–1.79/h) | $4–6 | $35–52 | $172–260 |
| Modal L40S 28x ($1.95/h) | $7.6 | $71 | $350 |
| OVH L40S 28x (EUR 1.40–1.80/h) | EUR 5.5–7 | EUR 50–65 | EUR 251–323 |
| Scaleway L4 9x (EUR 0.79/h) | EUR 9 | EUR 88 | EUR 439 |
| Hetzner GEX45 15x (EUR 0.343/h + EUR 209 setup, or EUR 214/mo) | EUR 2.4 + setup | EUR 23 + setup | EUR 115 + setup (about 333 h, i.e. one month at EUR 214 + 209) |
| Local 3060 Ti 7.5x | free (electricity) | 133 h | 667 h |

Hidden costs: storage for 70 GB of Opus audio on a network volume is about $5/month at RunPod rates; transferring 5,000 h by wire is the same either way; idle time is the one you control (section 3).

Parallelism: wall-clock for 5,000 h on one 4090 is ~200 h. Four pods in parallel cost the same and finish in ~2 days. Prefer that over one long run, because a pod failure then loses little.

## 3. Recommendation

**RunPod, RTX 4090 pods (Secure or Community, pick the cheapest with 24 GB and a CUDA 12.6-capable driver), launched and removed per batch.** Reasons: lowest cost per audio hour among providers with a real API, per-second billing, 24 GB leaves room for Whisper batch 16 and pyannote together, no commitment. Fallbacks: Vast.ai if RunPod 4090 stock is short (cheaper, more babysitting); OVHcloud L40S if the owner wants everything EU-hosted under an account he already has (about 1.5-2x the price; ask for GPU quota now because the ticket can take days); Hetzner GEX45 monthly if the 2023 backfill is the whole point and he wants a flat EUR 423 for the first month with unlimited traffic.

Before any of it: **do the batched-Whisper patch and concurrent diarization locally** (free; Whisper alone gets ~3.7x). On the PC, 1,000 h then takes roughly 2-3 days (14-24x equivalent is a 4090 figure; a 3060 Ti would be somewhat slower), so for 1,000 h the PC is fine. A rented GPU earns its place from about 2,000 h upward or when a deadline matters (debate night).

### Image contents (see `m3/gpu_runner/Dockerfile`)
- Base `nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04` (CUDA 12, cuDNN 9), venv with torch cu126, `faster-whisper==1.2.1`, `ctranslate2==4.8.3`, `pyannote.audio==4.0.7`, ffmpeg, rsync.
- **faster-whisper large-v3 baked in** (public model). **pyannote community-1 is gated, so it is downloaded at start with the runtime `HF_TOKEN`** (tiny). No token, key, voiceprint or people list in the image; `.dockerignore` excludes `data/`, `voiceprints/`, `logs/`.
- Only `src/` is copied in; `config/` and `voiceprints/` are pulled from the VPS at run time (voiceprints are biometric data; keep the image public-safe).

### Job flow
1. On the VPS, write `queue/gpu_batch.txt` with the item ids (folders under `data/raw/`). Ship audio as Opus/FLAC 16 kHz mono (about 14 MB/h) instead of wav; the runner converts to wav on the box.
2. Create the pod from the image with env `HF_TOKEN`, `DATA_HOST`, `SSH_KEY_B64` (a dedicated key, restricted on the VPS with `command="rrsync ..."` to `data/raw` read-only and `data/items` write), `STOP_CMD='runpodctl remove pod $RUNPOD_POD_ID'` (verify the pod's CLI/key setup on the first test), `MAX_MINUTES`.
3. `run.sh` pulls the batch, runs `src/process.py` (or batched variant with `BATCHED=1`), pushes `data/items/*.json` back, then **stops the pod in an `EXIT` trap**, plus a `MAX_MINUTES` watchdog.
4. VPS side: a small launcher script calls the RunPod API with a scoped API key (stored on the VPS, not on the pod), or the owner runs it by hand for backfills.

### Avoiding idle cost
- The pod terminates itself on success, failure or timeout (trap + watchdog); never leave a pod "waiting for work".
- Prefer removing over stopping a pod: stopped pods still bill volume storage.
- Small batches should be accumulated (for example one launch per day for campaign items, or when the queue exceeds ~10 h) so the 0.3 h startup is amortised.
- Spend cap: set a low RunPod account balance; the credit running out is the last-resort stop.
- Keep the Docker image on a registry close to the provider; first pull of ~12 GB takes minutes and is billed.

### Known gaps in the draft
- `process.py` starts a new Python process per stage per item, so the models reload for each item (~3-10 s). Fine for hours-long speeches, wasteful for thousands of 2-minute clips; a persistent worker loop would fix it.
- Dependency versions in the Dockerfile are partly unpinned (torch); pin them from `requirements.lock.txt` and `m1/pre_pyannote_freeze.txt`.
- `STOP_CMD` for RunPod is an assumption to check on the first (paid, tiny) test.
- Nothing was built or run.

## Sources
- RunPod pricing: https://www.runpod.io/pricing
- Vast.ai pricing: https://vast.ai/pricing; 4090 market data (3rd party): https://computeprices.com/providers/vast/gpus/rtx4090 , https://costbench.com/software/ai-gpu-cloud/vast-ai/
- Modal pricing: https://modal.com/pricing ; batching example: https://modal.com/docs/examples/batched_whisper
- Lambda pricing: https://lambda.ai/pricing
- Scaleway GPU pricing: https://www.scaleway.com/en/pricing/gpu/
- OVHcloud: https://www.ovhcloud.com/en/public-cloud/prices/ ; launch prices (3rd party): https://next.ink/brief-article/ovhcloud-les-instances-avec-gpu-h100-pcie-sont-disponibles-les-l40s-et-l4-au-printemps/
- Hetzner GPU line: https://www.hetzner.com/dedicated-rootserver/matrix-gpu/
- TensorDock (3rd party): https://deploybase.ai/articles/tensordock-gpu-pricing
- faster-whisper benchmarks: https://github.com/SYSTRAN/faster-whisper
- 4090 Whisper numbers (3rd party): https://gigagpu.com/rtx-4090-24gb-whisper-benchmark/ , https://www.spheron.network/blog/faster-whisper-gpu-cloud-production-deployment-guide/
- pyannote community-1 / speed: https://pypi.org/project/pyannote-audio/4.0.2/ , https://docs.rs/speakrs
