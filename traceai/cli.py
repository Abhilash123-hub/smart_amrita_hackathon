"""CLI Entry Point for TraceAI Multimodal Ingestion Gateway."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from traceai.config import GatewayConfig
from traceai.crypto.signer import CryptoSigner
from traceai.gateway import IngestionGateway


def setup_cli() -> argparse.ArgumentParser:
    """Build the command-line argument parser for TraceAI."""
    parser = argparse.ArgumentParser(
        prog="traceai",
        description="TraceAI: Multimodal Ingestion Gateway & Cryptographic Clearance System",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan and clear dataset assets")
    scan_parser.add_argument(
        "--input-dir",
        "-i",
        required=True,
        type=str,
        help="Path to directory or file containing raw text/image assets to ingest",
    )
    scan_parser.add_argument(
        "--index-dir",
        "-x",
        required=False,
        default=None,
        type=str,
        help="Path to pre-built copyright index directory",
    )
    scan_parser.add_argument(
        "--output",
        "-o",
        required=False,
        default=None,
        type=str,
        help="Optional path to write JSON scan report payload",
    )
    scan_parser.add_argument(
        "--private-key",
        "-k",
        required=False,
        default=None,
        type=str,
        help="Path to RSA private key PEM file for signing certificates (auto-generated if omitted)",
    )
    scan_parser.add_argument(
        "--text-threshold",
        type=float,
        default=0.85,
        help="Cross-encoder copyright risk threshold for text track (default: 0.85)",
    )
    scan_parser.add_argument(
        "--image-threshold",
        type=float,
        default=0.90,
        help="CLIP cosine similarity threshold for image track (default: 0.90)",
    )
    scan_parser.add_argument(
        "--minimal",
        action="store_true",
        help="Output minimal JSON format matching strict prompt schema",
    )

    # Command: generate-keys
    keys_parser = subparsers.add_parser("generate-keys", help="Generate RSA 2048-bit keypair for signing certificates")
    keys_parser.add_argument(
        "--output-dir",
        "-o",
        required=False,
        default="./keys",
        type=str,
        help="Directory to save generated private and public PEM files",
    )
    keys_parser.add_argument(
        "--key-size",
        type=int,
        default=2048,
        help="RSA key size in bits (default: 2048)",
    )

    # Command: verify-cert
    verify_parser = subparsers.add_parser("verify-cert", help="Verify an RSA-PSS signed clearance certificate")
    verify_parser.add_argument(
        "--asset-hash",
        required=True,
        type=str,
        help="The SHA-256 asset hash, e.g. 'sha256:...'",
    )
    verify_parser.add_argument(
        "--signature",
        required=True,
        type=str,
        help="Base64 encoded RSA-PSS signature string",
    )
    verify_parser.add_argument(
        "--public-key",
        required=True,
        type=str,
        help="Path to RSA public key PEM file",
    )

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Launch the interactive Web Platform dashboard")
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the web server (default: 8000)",
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind (default: 127.0.0.1)",
    )

    return parser


def run_scan_command(args: argparse.Namespace) -> int:
    """Execute the scan pipeline command."""
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"Error: Input path '{input_path}' does not exist.", file=sys.stderr)
        return 1

    config = GatewayConfig(
        text_cross_encoder_threshold=args.text_threshold,
        image_clip_cosine_threshold=args.image_threshold,
    )

    # Setup signer
    if args.private_key and Path(args.private_key).exists():
        signer = CryptoSigner.load_from_files(private_key_path=args.private_key)
    else:
        signer = CryptoSigner.generate(key_size=config.rsa_key_bits)

    gateway = IngestionGateway(config=config, signer=signer)

    # Run async scan
    report = asyncio.run(gateway.scan(input_path=input_path, index_dir=args.index_dir))

    # Format output payload
    output_payload = report.to_output_payload(minimal=args.minimal)
    payload_json = json.dumps(output_payload, indent=2)

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(payload_json, encoding="utf-8")
        print(f"[TraceAI] Scan completed. Output saved to {out_p}")
    else:
        print(payload_json)

    return 0 if report.summary.blocked_count == 0 else 2


def run_generate_keys_command(args: argparse.Namespace) -> int:
    """Generate RSA keypair and save to disk."""
    out_dir = Path(args.output_dir)
    signer = CryptoSigner.generate(key_size=args.key_size)
    priv_p, pub_p = signer.save_keys(out_dir)
    print(f"[TraceAI] Generated RSA {args.key_size}-bit keypair:")
    print(f"  Private Key: {priv_p}")
    print(f"  Public Key:  {pub_p}")
    print(f"  Fingerprint: {signer.key_fingerprint}")
    return 0


def run_verify_cert_command(args: argparse.Namespace) -> int:
    """Verify an asset signature using a public key PEM."""
    pub_path = Path(args.public_key)
    if not pub_path.exists():
        print(f"Error: Public key file '{pub_path}' not found.", file=sys.stderr)
        return 1

    signer = CryptoSigner.load_from_files(public_key_path=pub_path)
    is_valid = signer.verify_signature(args.asset_hash, args.signature)

    if is_valid:
        print(f"[TraceAI] SUCCESS: Signature is VALID for {args.asset_hash}")
        return 0
    else:
        print(f"[TraceAI] FAILED: Signature is INVALID for {args.asset_hash}", file=sys.stderr)
        return 1


def run_serve_command(args: argparse.Namespace) -> int:
    """Run the web platform application server."""
    import uvicorn
    print("=" * 70)
    print("🚀 Starting TraceAI Web Platform...")
    print(f"🌐 Running locally at: http://{args.host}:{args.port}")
    print(f"📄 API Documentation:  http://{args.host}:{args.port}/docs")
    print("=" * 70)
    uvicorn.run("traceai.api.server:app", host=args.host, port=args.port, reload=True)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = setup_cli()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "scan":
        return run_scan_command(args)
    elif args.command == "generate-keys":
        return run_generate_keys_command(args)
    elif args.command == "verify-cert":
        return run_verify_cert_command(args)
    elif args.command == "serve":
        return run_serve_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
