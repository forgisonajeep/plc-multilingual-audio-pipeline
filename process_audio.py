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
