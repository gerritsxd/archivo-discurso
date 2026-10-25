# Upgrade options: server and rented GPUs

*Checked 2026-10-25 on official pages. Nothing bought, no accounts made. Prices are "from" prices; VAT status is noted. Anything marked (unverified) I could not read on the page.*

**Short answer:** move to an 8 GB server now (about 8-9 per month), keep the audio on cheap object storage or a storage box once it passes ~50 GB, and rent a GPU only for a big backfill. The home PC is enough for the campaign.

## 1. The server

**The problem is RAM, not CPU.** The VPS has 3.7 GB and other services already use 2.9 GB. The archive, the SQLite API and the feed discovery need more than the ~0.8 GB left. Disk (30 GB free) is the second limit: 1,000 h of Opus is ~15 GB, but original MP3/M4A files (30-60 MB/h) would fill it at ~500-1,000 h.

### OVH VPS (official page ovhcloud.com/en/vps, prices in USD, page does not say if VAT is included; region not stated)

| Plan | vCores | RAM | Disk (NVMe) | Price / month |
|---|---|---|---|---|
| VPS-1 | 2 | 4 GB | 40 GB | $4.54 |
| **VPS-2** | 4 | 8 GB | 75 GB | **$8.50** |
| VPS-3 | 6 | 12 GB | 100 GB | $12.32 |
| VPS-4 | 8 | 24 GB | 200 GB | $23.37 |

All have unlimited traffic and daily backups. **VPS-2 fits**: it doubles RAM and leaves ~5 GB free after the current services plus room for a small API. VPS-1 has almost the same RAM as today, so it does not help.

**In place or new server?** OVH says "1-click scaling" lets you add resources without data migration and without disruption. I could not verify from the page whether this works from the current plan, or whether the disk can grow later (on many VPS lines, disk size cannot be reduced and the upgrade can reboot the machine). Easiest path: try the upgrade in the OVH panel. If the panel does not offer it, order a new VPS-2 in Frankfurt and move the services with rsync (about half a day). Take a snapshot first either way.

### Alternative: Hetzner Cloud (official, EUR, excl. VAT)

| Plan | vCPU | RAM | Disk | Price / month | Note |
|---|---|---|---|---|---|
| CX33 (cost-optimised) | 4 | 8 GB | 80 GB | 8.99 | **marked "currently unavailable" on the page today** |
| CAX21 (Arm) | 4 | 8 GB | 80 GB | 10.99 | also unavailable today; Arm means some Python wheels need checking |
| CPX32 (regular, EU: Nuremberg, Helsinki) | 4 | 8 GB | 160 GB | 35.99 | available, 4x the price |
| CPX22 | 2 | 4 GB | 80 GB | 19.99 | too little RAM |

Hetzner is good value when stock returns, but OVH VPS-2 is cheaper and you already have the account. Hetzner is **not** a fix for YouTube: it blocks data-centre IPs everywhere (see m0/GEO_TEST.md).

### Storage for the audio archive

| Option | Price (excl. VAT unless noted) | Good for |
|---|---|---|
| Disk on VPS-2 (75 GB) | included | up to ~4,000 h of Opus (60 GB), tight |
| Hetzner Storage Box BX11, 1 TB | EUR 3.20 / month | **cheapest per TB** (EUR 3.20/TB); BX21 5 TB EUR 10.90 (2.18/TB); BX31 10 TB EUR 20.80 |
| Hetzner Object Storage (S3) | EUR 6.49 / month incl. 1 TB storage + 1 TB egress; extra storage ~EUR 6.35/TB-month (0.0087/TB-hour), extra egress EUR 1.00/TB; ingress free | when you want an S3 link for GPU boxes |
| OVH Object Storage | OVH page says no charge for traffic or API calls; **per-TB price not readable, so unverified** | check on the OVH prices page before choosing |

**My pick:** Storage Box BX11 (EUR 3.20 per month, 1 TB) when the archive passes ~50 GB. 5,000 h of Opus is ~75 GB and even all originals for 5,000 h (~150-300 GB) fit in 1 TB. Keep it private (see ARCHITECTURE section 6). A Storage Box is reached over SFTP/rsync, not as a mounted disk, which is fine for an archive.

## 2. Renting a GPU (summary of m3/GPU_ON_DEMAND.md)

- Best fit: **RunPod RTX 4090 pods**, ~$0.31-0.89 per hour, billed per second, started and removed by a script; fallbacks Vast.ai (cheaper, more babysitting) and OVH L40S (EU, about EUR 1.40-1.80 per hour, GPU quota needs a ticket).
- Estimated speed on a 4090 with the batched Whisper patch: ~25x real time (about 3x the home PC's 7.5x). Without the patch ~14x. Treat as +/-40 %.
- Cost per audio hour: roughly $0.012-0.036 (batched). So 1,000 h is $12-36 and 5,000 h is $62-179.
- **When it is worth it:** not for the backlog (55 h = one evening at home) or the campaign (15-25 h per day = ~3 h of PC time). It pays off from **~2,000 h** upward or when a deadline matters (debate night). The break-even is time, not money: the PC is free but would need ~270 h (11 days non-stop) for 2,000 h and ~400 h (17 days) for 3,000 h.
- Always test one real hour first (~$0.50), and let the pod delete itself when it finishes.

### Kickstart scenario: backfill the 2023 campaign in one weekend

Assumption (my estimate, not measured): the 2023 general election campaign plus the weeks around it is **1,500-3,000 h** of raw audio. The m0 count was ~55 h in 3 weeks for six candidates; 2023 has more sources and more people, so this is a guess.

| Size | Audio to upload (Opus, ~15 MB/h) | 4090 compute | Wall clock on 4 pods in parallel | Cost (compute only) |
|---|---|---|---|---|
| 1,500 h | ~22 GB | ~60 h | ~15 h | **$19-54** |
| 3,000 h | ~45 GB | ~120 h | ~30 h (fits a weekend) | **$37-107** |
| 3,000 h, unpatched code (14x) | ~45 GB | ~215 h | ~54 h | $66-192 |

Add: ~$5 storage if you keep a network volume for a month, a few dollars for failed or test runs, VAT on top. **Plan on $50-150 total for one weekend.** Compared with the home PC: ~400 h for 3,000 h, about 17 days of the PC running day and night. Upload from home or the VPS is the likely bottleneck; the 45 GB must reach the pods.

## 3. Recommendation

| When | What | Monthly cost |
|---|---|---|
| **Now** | OVH VPS-2 (4 vCores, 8 GB, 75 GB); home PC for GPU and YouTube | ~$8.50 (about EUR 8-9, check VAT) |
| **When the archive passes ~50 GB** (about 3,000 h Opus, or ~1,000 h of originals) | Add Hetzner Storage Box BX11, 1 TB | + EUR 3.20 = **~12** |
| **If the project grows** (campaign running, several thousand h, public API traffic) | OVH VPS-3 (12 GB, 100 GB) or VPS-4 (24 GB, 200 GB) + Storage Box 1-5 TB | $12-23 + EUR 3-11 = **~15-35** |
| **One-off kickstart / debate peak** | RunPod 4090 pods, pay per use, no subscription | **$0 monthly**, $50-150 once for the 2023 backfill |
| **Not needed** | Spanish VPS (YouTube blocks data centres anyway); a permanent GPU server (Hetzner GEX45 EUR 214 per month + EUR 209 setup); larger Hetzner CPX plans; paid residential proxies; transcription on the VPS | 0 |

**Order of action:** (1) snapshot, then upgrade to VPS-2; (2) patch batched Whisper and test on the PC (free); (3) only if the 2023 backfill is wanted, run a $0.50 test on RunPod, then the weekend job.

## Not verified
- Whether the existing OVH VPS can be upgraded in place to VPS-2 (page says yes in general; the panel decides).
- OVH VPS prices are in USD with unclear VAT and region; the Frankfurt EUR price may differ.
- OVH object storage per-TB price.
- Hetzner CX/CAX stock (page showed "unavailable").
- The 2023 hours estimate and the GPU speeds (+/-40 %).
