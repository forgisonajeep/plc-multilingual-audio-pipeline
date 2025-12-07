# plc-multilingual-audio-pipeline-2025  

A fully automated, multilingual audio processing pipeline using Amazon Transcribe, Amazon Translate, Amazon Polly, and S3 event-driven architecture. GitHub Actions drive CI/CD and environment separation for beta and production runs.

[![Release v1 – foundational](https://img.shields.io/badge/release-v1--foundational--complete-blue)](https://github.com/forgisonajeep/plc-multilingual-audio-pipeline/tree/v1-foundational-complete)
[![Release v2 – advanced](https://img.shields.io/badge/release-v2--advanced--complete-purple)](https://github.com/forgisonajeep/plc-multilingual-audio-pipeline/tree/v2-advanced-complete)

[![Foundational PR – beta](https://github.com/forgisonajeep/plc-multilingual-audio-pipeline/actions/workflows/on_pull_request.yml/badge.svg)](../../actions/workflows/on_pull_request.yml)
[![Foundational Merge – prod](https://github.com/forgisonajeep/plc-multilingual-audio-pipeline/actions/workflows/on_merge.yml/badge.svg)](../../actions/workflows/on_merge.yml)
[![Advanced – upload audio (S3 event-driven)](https://github.com/forgisonajeep/plc-multilingual-audio-pipeline/actions/workflows/advanced_upload_audio.yml/badge.svg)](../../actions/workflows/advanced_upload_audio.yml)

---

## 🔗 Jump to section

- [1. Project overview](#1-project-overview)
- [2. Architecture](#2-architecture)
  - [2.1 Foundational (GitHub Actions only)](#21-foundational-github-actions-only)
  - [2.2 Advanced (S3-triggered Lambda)](#22-advanced-s3-triggered-lambda)
- [3. Repository structure](#3-repository-structure)
- [4. Phase 0 – Prerequisites](#sec-4)
- [5. Phase 1 – AWS setup](#sec-5)
- [6. Phase 2 – GitHub repo & secrets](#sec-6)
- [7. Phase 3 – Foundational pipeline (exact spec)](#sec-7)
- [8. Phase 4 – Advanced pipeline (exact-spec-s3–lambda)](#sec-8)
- [9. How to run the pipelines](#9-how-to-run-the-pipelines)
- [10. Verifying outputs in S3](#10-verifying-outputs-in-s3)
- [11. CloudWatch logging](#11-cloudwatch-logging)
- [12. Full workflow & code listings](#12-full-workflow--code-listings)
- [13. Cleanup & cost controls](#13-cleanup--cost-controls)
- [14. Version history](#14-version-history)
- [15. What’s next – Complex / IaC](#sec-15)

---

## 1. Project overview

Pixel Learning Co. (PLC) regularly uploads instructor `.mp3` audio and needs an automated way to:

- Transcribe English audio → text (Amazon Transcribe)  
- Translate transcripts into other languages (Amazon Translate)  
- Regenerate speech in the target language (Amazon Polly)  
- Store transcripts, translations, and audio outputs in Amazon S3 with **beta** and **prod** separation  

This repo implements that pipeline in two tiers:

- **Foundational (v1):** GitHub Actions call Transcribe / Translate / Polly directly  
- **Advanced:** GitHub Actions *only* upload audio to S3, then an **S3-triggered Lambda** runs the AI pipeline

All work is done against a single bucket:

- **Bucket:** `plc-multilingual-audio-pipeline-2025`  

---

## 2. Architecture

### 2.1 Foundational (GitHub Actions only)

- Source audio lives in the repo under `audio_inputs/`  
- A Python script, `process_audio.py`, runs in GitHub Actions and:
  - Uploads the `.mp3` to S3 under `beta/audio_inputs/` or `prod/audio_inputs/`
  - Starts a Transcribe job
  - Reads Transcribe output, translates with Translate
  - Synthesizes audio with Polly
  - Uploads:
    - `beta/transcripts/{filename}.txt`
    - `beta/translations/{filename}_{lang}.txt`
    - `beta/audio_outputs/{filename}_{lang}.mp3`
- **Environment:**
  - Pull requests → **beta** (`on_pull_request.yml`)
  - Merges to `main` → **prod** (`on_merge.yml`)

---

### 2.2 Advanced (S3-triggered Lambda)

- GitHub Actions workflow `advanced_upload_audio.yml`:
  - Uses repo secrets to assume AWS credentials
  - Reads exactly one `.mp3` in `audio_inputs/`  
  - Uploads it to `s3://plc-multilingual-audio-pipeline-2025/audio_inputs/advanced_sample.mp3`  
- S3 event notification (prefix `audio_inputs/`, suffix `.mp3`) triggers Lambda:

  - **Lambda function:** `plc-ml-audio-lambda-2025`  
  - Determines environment based on key:
    - `audio_inputs/...` → `env_prefix = "beta"` (for this project)  
  - Pipeline inside Lambda:
    - Start Transcribe job
    - Poll until `COMPLETED`
    - Download and normalize transcript JSON
    - Translate transcript text
    - Synthesize translated speech with Polly
    - Upload:
      - `beta/transcripts/{base}.txt`
      - `beta/translations/{base}_{lang}.txt`
      - `beta/audio_outputs/{base}_{lang}.mp3`
  - Writes detailed logs to **CloudWatch Logs**.

---

## 3. Repository structure

Minimal repo layout (after advanced is in place):

    plc-multilingual-audio-pipeline-2025/
        .github/
            workflows/
                on_pull_request.yml       # Foundational – PR (beta)
                on_merge.yml              # Foundational – merge to main (prod)
                advanced_upload_audio.yml # Advanced – upload-only, S3 event-driven
        audio_inputs/
            advanced_sample.mp3          # Demo audio file for both tiers
        process_audio.py                 # Foundational pipeline script (Transcribe/Translate/Polly)
        README.md                        # This file
        .gitignore

---

<h2 id="sec-4">4. Phase 0 – Prerequisites</h2>

You should already have:

- An AWS account with access to:
  - Amazon S3
  - Amazon Transcribe
  - Amazon Translate
  - Amazon Polly
  - AWS Lambda & CloudWatch Logs (for advanced)
- An IAM user or role with programmatic access keys
- Git, GitHub account, and VS Code

---

<h2 id="sec-5">5. Phase 1 – AWS setup</h2>

### 5.1 S3 bucket and automatic prefix creation (beta/prod)

This project uses a single S3 bucket to store all inputs and generated outputs.  
The folder structure (prefixes) is created automatically by the pipeline during the first execution — no manual folder creation was required.

**Bucket**  
- `plc-multilingual-audio-pipeline-2025`

**Prefixes created during the first run:**

- `audio_inputs/` — incoming `.mp3` uploads from GitHub Actions  
- `beta/transcripts/` — transcribed text output for beta runs  
- `beta/translations/` — translated text output for beta runs  
- `beta/audio_outputs/` — synthesized audio output for beta runs  
- `prod/...` — same structure for production runs (created after merging to `main`)

The pipeline determines `beta` or `prod` using:
- Pull Request events → `beta`
- Merge to main → `prod`

---

<h2 id="sec-6">6. Phase 2 – GitHub repo & secrets</h2>

### 6.1 Create the repository

- **Name:** `plc-multilingual-audio-pipeline`  
- Default branch: `main`  
- Add a `.gitignore` for Python/VS Code.

### 6.2 Configure GitHub secrets

In **Settings → Secrets and variables → Actions**, add:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` = `us-east-1`
- `S3_BUCKET` = `plc-multilingual-audio-pipeline-2025`

---

<h2 id="sec-7">7. Phase 3 – Foundational pipeline </h2>

This phase keeps **all processing inside GitHub Actions**.

### 7.1 Add demo audio

In the repo, place a single `.mp3` file:

- Path: `audio_inputs/multilingual_accessibility.mp3`  
- Later renamed to `advanced_sample.mp3` for advanced, but foundational runs still operate correctly against the file in `audio_inputs/`.

### 7.2 Implement `process_audio.py`

Responsibilities:

- Upload `.mp3` to S3 under a prefix that matches the environment:

  - Pull request → `beta/audio_inputs/{filename}.mp3`  
  - Merge to main → `prod/audio_inputs/{filename}.mp3`

- Start a Transcribe job against the S3 URI
- Poll Transcribe until status is `COMPLETED`
- Download and normalize transcript text
- Translate into a target language (configurable, e.g., Spanish `"es"`)
- Synthesize translated speech with Polly
- Upload outputs back to S3:

  - `beta/transcripts/{filename}.txt`
  - `beta/translations/{filename}_{lang}.txt`
  - `beta/audio_outputs/{filename}_{lang}.mp3`  

  (or `prod/...` for merges)

It also logs each step (`[STEP 1] Uploading input`, `[STEP 2] Waiting for Transcribe`, etc.) so GitHub Actions logs can double as troubleshooting output.

### 7.3 Foundational workflows

Two workflows:

1. **PR → beta** – `.github/workflows/on_pull_request.yml`  
   - Trigger: `pull_request` → base `main`
   - Steps:
     - Check out code  
     - `pip install` Boto3 and dependencies  
     - Run `python process_audio.py` with `ENV=beta`  
     - Process `.mp3` and upload to `beta/...` prefixes in S3

2. **Merge → prod** – `.github/workflows/on_merge.yml`  
   - Trigger: `push` → branch `main`
   - Same script, but passes `ENV=prod`
   - All outputs land under `prod/...` prefixes

### 7.4 Expected bucket folder layout

The pipeline automatically creates structured prefixes for each environment after the first successful run.

#### 7.4.1 Bucket root
```
plc-multilingual-audio-pipeline-2025
├── audio_inputs/
├── beta/
└── prod/
```

#### 7.4.2 `beta/` environment outputs
```
beta/
├── audio_inputs/       # uploaded source .mp3 files
├── audio_outputs/      # synthesized final audio output
├── transcribe_raw/     # full JSON from Transcribe
├── transcripts/        # cleaned transcript text
└── translations/       # translated text
```

#### 7.4.3 `prod/` environment outputs
```
prod/
├── audio_inputs/       # production uploads
├── audio_outputs/      # production audio output
├── transcripts_raw/    # raw transcript JSON
├── transcripts/        # final cleaned transcript text
└── translations/       # translated text
```

---

<h2 id="sec-8">8. Phase 4 – Advanced pipeline (S3 + Lambda)</h2>

The **advanced** level moves the Transcribe/Translate/Polly work into an **event-driven Lambda**. GitHub Actions now only uploads audio and tags it.

### 8.1 Prepare the demo audio for advanced

Rename the repo audio file:

    git mv audio_inputs/multilingual_accessibility.mp3 audio_inputs/advanced_sample.mp3
    git commit -m "feat(advanced): rename audio to advanced_sample.mp3"
    git push

The same file is used for both tiers, but the name now clearly signals “advanced.”

### 8.2 Lambda IAM role & permissions

Create an execution role for the Lambda function (`plc-ml-audio-lambda-2025-role`) with:

- Trust policy: allows `lambda.amazonaws.com`
- Permissions:
  - Read/write to `plc-multilingual-audio-pipeline-2025` with least privilege
    - `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the bucket and its objects
  - Access to:
    - `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`
    - `translate:TranslateText`
    - `polly:SynthesizeSpeech`
  - Basic Lambda logging policy for CloudWatch Logs

#### 8.2.1 IAM policy JSON (least-privilege for this project)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::plc-multilingual-audio-pipeline-2025",
        "arn:aws:s3:::plc-multilingual-audio-pipeline-2025/*"
      ]
    },
    {
      "Sid": "TranscribePermissions",
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Sid": "TranslatePermissions",
      "Effect": "Allow",
      "Action": [
        "translate:TranslateText"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PollyPermissions",
      "Effect": "Allow",
      "Action": [
        "polly:SynthesizeSpeech"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### 8.3 Lambda function: `plc-ml-audio-lambda-2025`

Create a Python 3.x Lambda function with:

- **Handler:** `lambda_function.lambda_handler`
- **Environment variables:**

  - `S3_BUCKET` = `plc-multilingual-audio-pipeline-2025`
  - `SOURCE_LANG_CODE` = `en-US`
  - `TARGET_LANG_CODE` = `es`
  - `POLLY_VOICE_ID` = a Spanish voice such as `Lucia`

- **Core logic** (high level):

  - Parse the S3 event record:
    - Bucket name and object key (`audio_inputs/advanced_sample.mp3`)
  - Determine environment prefix:
    - For this project: any key under `audio_inputs/` → `env_prefix = "beta"`
  - Build input & output paths:

    - Input URI: `s3://plc-multilingual-audio-pipeline-2025/audio_inputs/advanced_sample.mp3`
    - Outputs:
      - `beta/transcripts/advanced_sample.txt`
      - `beta/translations/advanced_sample_es.txt`
      - `beta/audio_outputs/advanced_sample_es.mp3`

  - Log helpful messages:

    - `ENV=beta`
    - `Bucket=plc-multilingual-audio-pipeline-2025`
    - `Input key=audio_inputs/advanced_sample.mp3`
    - `Running Transcribe job: advanced_sample-<timestamp>`
    - `Transcribe status: IN_PROGRESS / COMPLETED`
    - `Wrote transcript to beta/transcripts/...`
    - `Running Translate`
    - `Running Polly`
    - `Wrote translated text / synthesized audio to beta/...`

### 8.4 S3 event trigger

Configure an S3 trigger on the bucket:

- **Event:** `PUT` (ObjectCreated)  
- **Prefix:** `audio_inputs/`  
- **Suffix:** `.mp3`  
- **Destination Lambda:** `plc-ml-audio-lambda-2025`  

This ensures that when GitHub Actions upload any `.mp3` to `audio_inputs/`, Lambda runs automatically.

### 8.5 Advanced GitHub Actions workflow

`advanced_upload_audio.yml` is the **advanced** workflow that now does *only*:

- Configure AWS credentials from secrets
- Ensure there is exactly **one** `.mp3` in `audio_inputs/`
- Upload it to S3:

  - `s3://plc-multilingual-audio-pipeline-2025/audio_inputs/advanced_sample.mp3`

- (Optional) Tag object metadata with `env=beta` for future extension

This workflow runs on:

- `pull_request` → **Advanced – Upload audio (S3 event-driven)**  
  - For **beta demo** runs, branch names like `advanced-beta-demo`.

### 8.6 Repository tree

```bash
plc-multilingual-audio-pipeline-2025/
│
├─ .github/
│   └─ workflows/
│       ├─ on_pull_request.yml
│       ├─ on_merge.yml
│       └─ advanced_upload_audio.yml
│
├─ audio_inputs/
│   └─ advanced_sample.mp3
│
├─ process_audio.py
├─ README.md
└─ .gitignore
```

---

## 9. How to run the pipelines

### 9.1 Run foundational beta (PR)

1. Create a feature branch from `main`, e.g. `foundational-2025-exact-spec`  
2. Commit + push changes (or just the `.mp3` and script).  
3. Open a **Pull Request** into `main`.  
4. GitHub Actions runs `on_pull_request.yml`:

   - Job: `process-audio-beta`  
   - Environment: `ENV=beta`  
   - Outputs: `beta/...` prefixes

### 9.2 Run foundational prod (merge)

1. Once beta is passing, merge the PR into `main`.  
2. This triggers `on_merge.yml`:

   - Job: `process-audio-prod`  
   - Environment: `ENV=prod`  
   - Outputs: `prod/...` prefixes

### 9.3 Run advanced beta (S3 event-driven)

1. Ensure `audio_inputs/advanced_sample.mp3` is present.  
2. Create a branch, e.g. `advanced-beta-demo`.  
3. Make a small change (e.g., README line), commit, and push.  
4. Open a PR → `main`:

   - Workflow `advanced_upload_audio.yml` runs:
     - Uploads `advanced_sample.mp3` to `audio_inputs/` in S3  
     - S3 event triggers the Lambda
5. Lambda runs the full pipeline and writes outputs to `beta/...`.

---

## 10. Verifying outputs in S3

To confirm the system end-to-end:

1. **Bucket layout**  
   - `audio_inputs/advanced_sample.mp3`  
   - `beta/transcripts/advanced_sample.txt`  
   - `beta/translations/advanced_sample_es.txt`  
   - `beta/audio_outputs/advanced_sample_es.mp3`  
   - (Plus `prod/...` equivalents for foundational)

2. **Open the transcript**  
   - Download `advanced_sample.txt`  
   - Confirm that English text matches the spoken audio.

3. **Open the translation**  
   - Download `advanced_sample_es.txt`  
   - Confirm the translation is in Spanish.

4. **Play the Spanish audio**  
   - Download `advanced_sample_es.mp3`  
   - Confirm Polly generated natural-sounding speech in Spanish.

---

## 11. CloudWatch logging

Lambda writes detailed logs to a log group like:

- `/aws/lambda/plc-ml-audio-lambda-2025`

Key lines to look for in the latest log stream:

- `Found credentials in environment variables.`  
- `ENV=beta`  
- `Bucket=plc-multilingual-audio-pipeline-2025`  
- `Input key=audio_inputs/advanced_sample.mp3`  
- `Running Transcribe job: advanced_sample-...`  
- `Transcribe status: IN_PROGRESS` (repeated)  
- `Transcribe status: COMPLETED`  
- `Wrote transcript to beta/transcripts/advanced_sample.txt`  
- `Running Translate`  
- `Running Polly`  
- `Wrote translated text to beta/translations/...`  
- `Wrote synthesized audio to beta/audio_outputs/...`

This log stream proves that **S3, Lambda, Transcribe, Translate, Polly, and S3 outputs are all wired together.**

---

## 12. Full workflow & code listings


### 12.1 `.github/workflows/on_pull_request.yml` – Foundational PR (beta)

```yaml
name: Foundational - PR (beta) / process-audio-beta

on:
  # Foundational pipeline is frozen after v1-foundational-complete.
  # This workflow is now manual-only so advanced pipelines can own PR traffic.
  workflow_dispatch:

jobs:
  process-audio-beta:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install boto3

      - name: Process audio with Transcribe, Translate, Polly (beta)
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ${{ secrets.AWS_REGION }}
          S3_BUCKET: ${{ secrets.S3_BUCKET }}
          TARGET_LANG: "es"       # configurable target language
          ENV_PREFIX: "beta"      # <- this makes paths beta/...
        run: python process_audio.py

```

### 12.2 `.github/workflows/on_merge.yml` – Foundational Merge (prod)
    
```yaml
name: Foundational - main (prod) / process-audio-prod

on:
  # Foundational pipeline is frozen after v1-foundational-complete.
  # This workflow is now manual-only so advanced pipelines can own main pushes.
  workflow_dispatch:

jobs:
  process-audio-prod:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install boto3

      - name: Process audio with Transcribe, Translate, Polly (prod)
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ${{ secrets.AWS_REGION }}
          S3_BUCKET: ${{ secrets.S3_BUCKET }}
          TARGET_LANG: "es"
          ENV_PREFIX: "prod"      # <- this makes paths prod/...
        run: python process_audio.py
```

### 12.3 `.github/workflows/advanced_upload_audio.yml` – Advanced upload-only workflow

````yaml
# Demo: advanced beta run
name: Advanced - Upload audio (S3 event-driven)

on:
  pull_request:
    branches: [ main ]
    paths:
      - "audio_inputs/**"
      - ".github/workflows/advanced_upload_audio.yml"
  push:
    branches: [ main ]
    paths:
      - "audio_inputs/**"
      - ".github/workflows/advanced_upload_audio.yml"

jobs:
  upload-audio:
    runs-on: ubuntu-latest

    permissions:
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Determine tier (beta on PR, prod on push)
        id: tier
        shell: bash
        run: |
          if [[ "${{ github.event_name }}" == "pull_request" ]]; then
            echo "TIER=beta" >> "$GITHUB_OUTPUT"
          else
            echo "TIER=prod" >> "$GITHUB_OUTPUT"
          fi
          echo "ACTIVE_TIER=${{ steps.tier.outputs.TIER }}"

      - name: Guard bucket secret present
        shell: bash
        run: |
          if [[ -z "${{ secrets.S3_BUCKET }}" ]]; then
            echo "::error::S3_BUCKET secret is empty or unset." >&2
            exit 1
          fi
          echo "Bucket: ${{ secrets.S3_BUCKET }}"

      - name: Verify source MP3 exists in repo (exactly one)
        shell: bash
        run: |
          shopt -s nullglob
          FILES=(audio_inputs/*.mp3)
          COUNT=${#FILES[@]}

          if (( "$COUNT" != 1 )); then
            echo "::error::One and only one MP3 file must exist in audio_inputs/. Found: $COUNT" >&2
            exit 1
          fi
          echo "Using MP3 file: ${FILES[0]}"

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Upload MP3 to S3 (triggers Lambda)
        shell: bash
        run: |
          FILE_PATH=$(ls audio_inputs/*.mp3)
          FILE_NAME=$(basename "$FILE_PATH")
          aws s3 cp "$FILE_PATH" "s3://${{ secrets.S3_BUCKET }}/audio_inputs/$FILE_NAME" \
            --metadata env=${{ steps.tier.outputs.TIER }}
````

### 12.4 `process_audio.py` – Foundational pipeline script

````yaml
import os
import time
import json
from typing import Tuple

import boto3


def get_env(name: str, required: bool = True, default: str | None = None) -> str:
    """Helper to read env vars with a clear error if missing."""
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def find_first_mp3(input_dir: str = "audio_inputs") -> str:
    """
    Find the first .mp3 file under audio_inputs/.
    Raises if none are found.
    """
    if not os.path.isdir(input_dir):
        raise RuntimeError(f"Input folder not found: {input_dir}")

    for entry in os.listdir(input_dir):
        if entry.lower().endswith(".mp3"):
            return os.path.join(input_dir, entry)

    raise RuntimeError(f"No .mp3 files found in {input_dir}/")


def choose_polly_voice(target_lang: str) -> Tuple[str, str]:
    """
    Pick a Polly VoiceId and LanguageCode based on the target language.
    Defaults to Joanna / en-US if unknown.
    """
    lang = target_lang.lower()

    if lang.startswith("es"):  # Spanish
        return "Lucia", "es-ES"
    if lang.startswith("fr"):  # French
        return "Celine", "fr-FR"
    if lang.startswith("en"):  # English
        return "Joanna", "en-US"

    # Fallback
    return "Joanna", "en-US"


def main() -> None:
    # --- Environment variables from GitHub Actions ---
    aws_region = get_env("AWS_REGION", required=True)
    s3_bucket = get_env("S3_BUCKET", required=True)
    target_lang = get_env("TARGET_LANG", required=False, default="es")
    env_prefix = get_env("ENV_PREFIX", required=False, default="beta")  # "beta" or "prod"

    print(f"[INFO] Region: {aws_region}")
    print(f"[INFO] S3 bucket: {s3_bucket}")
    print(f"[INFO] Target language: {target_lang}")
    print(f"[INFO] Environment prefix: {env_prefix}")

    # --- Locate MP3 input ---
    local_mp3_path = find_first_mp3("audio_inputs")
    filename = os.path.basename(local_mp3_path)
    basename, _ = os.path.splitext(filename)

    print(f"[INFO] Found audio file: {local_mp3_path}")

    # --- Build S3 keys (match spec: env/ folder prefixes) ---
    input_key = f"{env_prefix}/audio_inputs/{filename}"
    raw_json_key = f"{env_prefix}/transcripts_raw/{basename}.json"
    transcript_key = f"{env_prefix}/transcripts/{basename}.txt"
    translation_key = f"{env_prefix}/translations/{basename}_{target_lang}.txt"
    audio_out_key = f"{env_prefix}/audio_outputs/{basename}_{target_lang}.mp3"

    # --- Create AWS clients ---
    s3 = boto3.client("s3", region_name=aws_region)
    transcribe = boto3.client("transcribe", region_name=aws_region)
    translate = boto3.client("translate", region_name=aws_region)
    polly = boto3.client("polly", region_name=aws_region)

    # ========== STEP 1: Upload MP3 to S3 ==========
    print(f"[STEP 1] Uploading input audio to s3://{s3_bucket}/{input_key}")
    s3.upload_file(local_mp3_path, s3_bucket, input_key)
    media_s3_uri = f"s3://{s3_bucket}/{input_key}"

    # ========== STEP 2: Transcribe (Amazon Transcribe) ==========
    job_name = f"plc-audio-{basename}-{int(time.time())}"
    print(f"[STEP 2] Starting Transcribe job: {job_name}")

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        LanguageCode="en-US",  # assuming original audio is English
        Media={"MediaFileUri": media_s3_uri},
        OutputBucketName=s3_bucket,
        OutputKey=raw_json_key,  # where raw JSON transcript is stored
    )

    # Poll for completion
    while True:
        resp = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        status = resp["TranscriptionJob"]["TranscriptionJobStatus"]
        print(f"[Transcribe] Job status: {status}")
        if status == "COMPLETED":
            break
        if status == "FAILED":
            reason = resp["TranscriptionJob"].get("FailureReason", "Unknown")
            raise RuntimeError(f"Transcription job failed: {reason}")
        time.sleep(5)

    print(f"[Transcribe] Completed. Raw JSON at s3://{s3_bucket}/{raw_json_key}")

    # Download raw transcript JSON from S3
    raw_obj = s3.get_object(Bucket=s3_bucket, Key=raw_json_key)
    raw_body = raw_obj["Body"].read().decode("utf-8")
    raw_json = json.loads(raw_body)

    # Extract transcript text
    transcript_text = raw_json["results"]["transcripts"][0]["transcript"]
    print(f"[Transcribe] Extracted transcript characters: {len(transcript_text)}")

    # Save clean transcript to S3 (text file)
    s3.put_object(
        Bucket=s3_bucket,
        Key=transcript_key,
        Body=transcript_text.encode("utf-8"),
        ContentType="text/plain",
    )
    print(f"[STEP 2] Saved clean transcript to s3://{s3_bucket}/{transcript_key}")

    # ========== STEP 3: Translate (Amazon Translate) ==========
    print(f"[STEP 3] Translating transcript to {target_lang}")
    translate_resp = translate.translate_text(
        Text=transcript_text,
        SourceLanguageCode="en",
        TargetLanguageCode=target_lang,
    )
    translated_text = translate_resp["TranslatedText"]

    # Save translation to S3
    s3.put_object(
        Bucket=s3_bucket,
        Key=translation_key,
        Body=translated_text.encode("utf-8"),
        ContentType="text/plain",
    )
    print(f"[STEP 3] Saved translation to s3://{s3_bucket}/{translation_key}")

    # ========== STEP 4: Synthesize (Amazon Polly) ==========
    voice_id, language_code = choose_polly_voice(target_lang)
    print(f"[STEP 4] Synthesizing speech with Polly (VoiceId={voice_id}, Lang={language_code})")

    polly_resp = polly.synthesize_speech(
        Text=translated_text,
        OutputFormat="mp3",
        VoiceId=voice_id,
    )

    audio_bytes = polly_resp["AudioStream"].read()

    # Upload synthesized audio to S3
    s3.put_object(
        Bucket=s3_bucket,
        Key=audio_out_key,
        Body=audio_bytes,
        ContentType="audio/mpeg",
    )
    print(f"[STEP 4] Saved synthesized audio to s3://{s3_bucket}/{audio_out_key}")

    print("[DONE] Foundational pipeline complete.")


if __name__ == "__main__":
    main()
````

### 12.5 `lambda_function.py` – Advanced S3-triggered Lambda

```yaml
import json
import os
import time
import logging
import urllib.parse

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
transcribe = boto3.client("transcribe")
translate = boto3.client("translate")
polly = boto3.client("polly")


def lambda_handler(event, context):
    """
    Event-driven multilingual audio pipeline.
    Triggered by S3 when a new .mp3 is uploaded under audio_inputs/.
    Steps:
      1. Figure out env (beta/prod) from object metadata (env=...).
      2. Run Transcribe on the uploaded MP3.
      3. Translate transcript to target language.
      4. Use Polly to synthesize translated speech.
      5. Write outputs under:
         <env>/transcripts/
         <env>/translations/
         <env>/audio_outputs/
    """

    logger.info("EVENT: %s", json.dumps(event))

    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

    # ---------- ENV / PREFIX RESOLUTION ----------
    # Try to read env from object metadata, e.g. metadata: {"env": "beta"}
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        metadata = head.get("Metadata", {})
    except ClientError as e:
        logger.error("head_object failed: %s", e)
        metadata = {}

    env_prefix = metadata.get("env", "beta")  # default to beta if not set

    # base filename w/o path or extension, e.g. advanced_sample
    file_name = os.path.basename(key)
    base_name = os.path.splitext(file_name)[0]

    logger.info("ENV=%s", env_prefix)
    logger.info("Bucket=%s", bucket)
    logger.info("Input key=%s", key)

    input_uri = f"s3://{bucket}/{key}"
    logger.info("Input URI=%s", input_uri)

    # ---------- CONFIGURABLE SETTINGS ----------
    source_lang = os.getenv("SOURCE_LANG_CODE", "en-US")  # Transcribe language
    target_lang = os.getenv("TARGET_LANG_CODE", "es")      # Translate target (ISO 639-1)
    polly_voice = os.getenv("POLLY_VOICE_ID", "Lucia")     # Any valid Polly voice

    logger.info(
        "Source language=%s, Target language=%s, Voice=%s",
        source_lang,
        target_lang,
        polly_voice,
    )

    # ---------- STEP 1: TRANSCRIBE ----------
    job_name = f"{base_name}-{int(time.time())}"
    logger.info("Running Transcribe job: %s", job_name)

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": input_uri},
        MediaFormat="mp3",
        LanguageCode=source_lang,
        OutputBucketName=bucket,
        OutputKey=f"{env_prefix}/transcribe_raw/{job_name}.json",
    )

    # Wait for job to complete
    while True:
        status = transcribe.get_transcription_job(  # <-- correct method
            TranscriptionJobName=job_name
        )
        job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
        logger.info("Transcribe status: %s", job_status)

        if job_status in ("COMPLETED", "FAILED"):
            break

        time.sleep(5)

    if job_status == "FAILED":
        logger.error("Transcription job failed: %s", status)
        raise RuntimeError("Transcription failed")

    # Where Transcribe put the JSON (we told it explicitly above)
    transcribe_key = f"{env_prefix}/transcribe_raw/{job_name}.json"
    logger.info("Transcribe output key: %s", transcribe_key)

    transcribe_obj = s3.get_object(Bucket=bucket, Key=transcribe_key)
    transcribe_data = json.loads(transcribe_obj["Body"].read())
    transcript_text = transcribe_data["results"]["transcripts"][0]["transcript"]

    # Save cleaned transcript into transcripts/<file>.txt
    transcript_key = f"{env_prefix}/transcripts/{base_name}.txt"
    s3.put_object(
        Bucket=bucket,
        Key=transcript_key,
        Body=transcript_text.encode("utf-8"),
    )
    logger.info("Wrote transcript to %s", transcript_key)

    # ---------- STEP 2: TRANSLATE ----------
    logger.info("Running Translate")
    translate_resp = translate.translate_text(
        Text=transcript_text,
        SourceLanguageCode=source_lang[:2],  # 'en-US' -> 'en'
        TargetLanguageCode=target_lang,
    )
    translated_text = translate_resp["TranslatedText"]

    translation_key = f"{env_prefix}/translations/{base_name}_{target_lang}.txt"
    s3.put_object(
        Bucket=bucket,
        Key=translation_key,
        Body=translated_text.encode("utf-8"),
    )
    logger.info("Wrote translation to %s", translation_key)

    # ---------- STEP 3: POLLY ----------
    logger.info("Running Polly")
    polly_resp = polly.synthesize_speech(
        Text=translated_text,
        OutputFormat="mp3",
        VoiceId=polly_voice,
        Engine="standard",
    )

    audio_bytes = polly_resp["AudioStream"].read()

    audio_key = f"{env_prefix}/audio_outputs/{base_name}_{target_lang}.mp3"
    s3.put_object(
        Bucket=bucket,
        Key=audio_key,
        Body=audio_bytes,
        ContentType="audio/mpeg",
    )
    logger.info("Wrote synthesized audio to %s", audio_key)

    # ---------- DONE ----------
    logger.info("Pipeline complete for %s", key)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "env": env_prefix,
                "bucket": bucket,
                "input_key": key,
                "transcript_key": transcript_key,
                "translation_key": translation_key,
                "audio_key": audio_key,
            }
        ),
    }
```
---

## 13. Cleanup & cost controls

This project uses fully serverless components that minimize cost:

- **Lambda** — pay-per-execution, no idle cost  
- **S3 Standard** — low storage cost for small input/output files  
- **Transcribe, Translate, Polly** — usage-based pricing only when invoked  
- **GitHub Actions** — free tier covers light usage

To avoid unnecessary charges during testing:

- Remove temporary `.mp3` inputs from `audio_inputs/`
- Delete unused result files in `beta/` and `prod/` if no longer needed
- Disable or remove unused S3 Event Notifications
- Delete the Lambda or detach the trigger when project is archived

The project can be safely paused by disabling:
- All GitHub Actions workflows
- S3 → Lambda event trigger (keeps bucket and results intact)

---

## 14. Version history

- **`v1-foundational-complete` tag**
  - Snapshot after finishing the exact-spec foundational pipeline:
    - `process_audio.py` complete
    - `on_pull_request.yml` and `on_merge.yml` wired to beta/prod
    - S3 bucket prefixes created and validated

- **Advanced (S3 event-driven)**
  - Implemented after v1 tag:
    - Lambda `plc-ml-audio-lambda-2025`
    - S3 event notifications on `audio_inputs/*.mp3`
    - `advanced_upload_audio.yml` upload-only workflow
    - CloudWatch logs and beta outputs verified

---

<h2 id="sec-15">15. What’s next – Complex / IaC</h2>

A future **Complex** version of this project will:

- Move all AWS resources into **Infrastructure-as-Code** (CloudFormation or Terraform)
- Use parameters for `env` (beta/prod) so the same template can deploy multiple stacks
- Add CI/CD to deploy infrastructure via GitHub Actions (`aws cloudformation deploy` or `terraform apply`)
- Optionally add:
  - S3 object lifecycle rules (30-day retention)
  - API Gateway + Lambda for querying completed outputs
  - AWS Step Functions for a multi-step orchestrated workflow

This project demonstrates a complete multilingual audio-processing pipeline using AWS Transcribe, Translate, and Polly, driven by GitHub Actions (beta/prod) and a fully event-driven Lambda integration. The architecture is intentionally designed to scale, while staying simple and serverless for experimentation and extension.
