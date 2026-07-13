#!/usr/bin/env python
"""
Run with the Chemistry Companion server running:

    python scripts/verify_ai_chain_recommendation.py data/4duh.pdb --ligand "your_ligand_smiles" --target "BRAF"

The script will produce a clean expert report you can screenshot or paste.
"""
"""
scripts/verify_ai_chain_recommendation.py
=========================================

Practical verification script for the AI Expert Chain Recommendation feature
(Phase 1c of the Advanced Docking Platform).

Usage:
    python scripts/verify_ai_chain_recommendation.py path/to/your_protein.pdb [--ligand SMILES] [--target "Target Name"]

This script:
- Reads a real multi-chain PDB (e.g. 4duh or any drug target)
- Runs the existing protein analysis
- Calls the new AI expert chain recommender
- Prints a beautiful, expert-style report you can copy into notes/slides

It is designed to be run from the Chemistry Companion root directory
while the server is running (it hits the local API).
"""

import argparse
import json
import sys
from pathlib import Path
import requests

API_BASE = "http://localhost:8000/api/docking"


def main():
    parser = argparse.ArgumentParser(description="Verify AI Expert Chain Recommendation on a real PDB")
    parser.add_argument("pdb_file", help="Path to a multi-chain PDB file (e.g. 4duh.pdb)")
    parser.add_argument("--ligand", "-l", default=None, help="Optional ligand SMILES for context")
    parser.add_argument("--target", "-t", default=None, help="Optional target name (e.g. 'BRAF Kinase')")
    parser.add_argument("--server", default="http://localhost:8000", help="Base URL of the running server")
    args = parser.parse_args()

    pdb_path = Path(args.pdb_file)
    if not pdb_path.exists():
        print(f"ERROR: File not found: {pdb_path}")
        sys.exit(1)

    print("=" * 70)
    print("ADVANCED DOCKING PLATFORM - AI EXPERT CHAIN RECOMMENDATION VERIFICATION")
    print("=" * 70)
    print(f"PDB file     : {pdb_path}")
    print(f"Ligand       : {args.ligand or '(none provided)'}")
    print(f"Target       : {args.target or '(none provided)'}")
    print(f"Server       : {args.server}")
    print()

    # 1. Read the PDB
    print("[1/3] Reading PDB file...")
    try:
        pdb_text = pdb_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  Failed to read file: {e}")
        sys.exit(1)
    print(f"  Loaded {len(pdb_text):,} bytes")

    # 2. Call protein analysis (the existing Phase 1a endpoint)
    print("\n[2/3] Running protein structure analysis (chain detection)...")
    try:
        resp = requests.post(
            f"{args.server}/api/docking/protein_analyze",
            json={"pdb_text": pdb_text},
            timeout=60
        )
        resp.raise_for_status()
        analysis = resp.json()
    except Exception as e:
        print(f"  ERROR contacting /protein_analyze: {e}")
        print("  Make sure the Chemistry Companion server is running.")
        sys.exit(1)

    print(f"  Found {analysis['total_chains']} chain(s), {analysis['total_residues']} residues")
    print(f"  Heuristic recommendation: {analysis.get('recommendation', {}).get('recommended_chain_ids', [])}")
    print(f"  Heuristic rationale     : {analysis.get('recommendation', {}).get('rationale', '(none)')}")

    # 3. Call the new AI expert recommendation
    print("\n[3/3] Consulting the 25-year docking expert (AI)...")
    try:
        ai_resp = requests.post(
            f"{args.server}/api/docking/ai_chain_recommendation",
            json={
                "analysis": analysis,
                "ligand_smiles": args.ligand,
                "target_name": args.target
            },
            timeout=120  # LLM calls can be slow
        )
        ai_resp.raise_for_status()
        ai_rec = ai_resp.json()
    except Exception as e:
        print(f"  ERROR calling AI recommendation: {e}")
        print("  This may be due to missing LLM API keys or network issues.")
        sys.exit(1)

    # === Beautiful Expert Report ===
    print("\n" + "=" * 70)
    print("AI EXPERT CHAIN RECOMMENDATION REPORT")
    print("=" * 70)

    source = ai_rec.get("source", "unknown")
    if source == "ai_expert":
        print("Source: AI Expert (25-year docking scientist simulation)")
    else:
        print(f"Source: {source} (fallback)")

    print(f"\nRecommended chain(s): {ai_rec.get('recommended_chain_ids', [])}")
    print(f"Confidence            : {ai_rec.get('confidence', 'unknown').upper()}")

    rationale = ai_rec.get("rationale", "(no rationale returned)")
    print("\n--- Expert Rationale ---")
    print(rationale)

    warnings = ai_rec.get("warnings", [])
    if warnings:
        print("\n--- Warnings ---")
        for w in warnings:
            print(f"• {w}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

    if source == "ai_expert":
        print("\nSUCCESS: The AI expert produced a structured recommendation.")
        print("You can now use this in the Docking Workspace UI and it will be")
        print("persisted in the job report under protein_preparation.analysis.")
    else:
        print("\nNOTE: Fell back to heuristic. Check LLM configuration / API keys.")

    # Also print raw JSON for power users
    print("\n--- Raw AI Response (for debugging) ---")
    print(json.dumps(ai_rec, indent=2))


if __name__ == "__main__":
    main()