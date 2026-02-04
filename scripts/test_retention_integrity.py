#!/usr/bin/env python3
"""
Test the retention system's audit chain preservation.

This verifies that:
1. Retention correctly identifies checkpoints
2. Chain integrity is maintained after retention runs
3. Export includes hash chain data

Usage:
  export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/wingman"
  python scripts/test_retention_integrity.py
"""

import os
import sys
import asyncio
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from homelab.storage.retention import retention_manager


async def test_retention(db_url: str) -> int:
    """Test retention system with audit chain verification."""
    
    print("=" * 60)
    print("Retention System - Audit Chain Integrity Test".center(60))
    print("=" * 60)
    print()
    
    engine = create_async_engine(db_url, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # 1. Verify audit integrity
        print("📊 Audit Integrity Report")
        print("-" * 40)
        
        report = await retention_manager.verify_audit_integrity(session)
        
        print(f"  Chain valid: {'✅' if report['is_valid'] else '❌'} {report['is_valid']}")
        print(f"  Total entries: {report['total_entries']}")
        print(f"  Violations: {len(report['violations'])}")
        print(f"  Checkpoints: {len(report['checkpoints'])}")
        print()
        
        if report['checkpoints']:
            print("  Checkpoints found:")
            for cp in report['checkpoints']:
                print(f"    - [{cp['type']:8s}] seq={cp['sequence_num']:3d}, "
                      f"hash={cp['entry_hash']}, ts={cp['timestamp'][:19]}")
        print()
        
        # 2. Test export (to temp directory)
        print("📦 Testing Export")
        print("-" * 40)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            exported = await retention_manager.export_audit_entries(session, tmpdir)
            print(f"  Exported {exported} entries to temp directory")
            
            # Check exported file
            import os
            import json
            files = os.listdir(tmpdir)
            if files:
                export_file = os.path.join(tmpdir, files[0])
                with open(export_file) as f:
                    export_data = json.load(f)
                
                print(f"  Export file: {files[0]}")
                print(f"  Export timestamp: {export_data.get('exported_at', 'N/A')[:19]}")
                print(f"  Sequence range: {export_data.get('first_sequence')} to {export_data.get('last_sequence')}")
                
                # Check that entries have hash chain data
                if export_data.get('entries'):
                    entry = export_data['entries'][0]
                    has_hash = 'entry_hash' in entry and entry['entry_hash']
                    has_prev = 'prev_hash' in entry and entry['prev_hash']
                    has_seq = 'sequence_num' in entry
                    
                    print()
                    print("  Hash chain data in export:")
                    print(f"    entry_hash: {'✅' if has_hash else '❌'}")
                    print(f"    prev_hash:  {'✅' if has_prev else '❌'}")
                    print(f"    sequence_num: {'✅' if has_seq else '❌'}")
            else:
                print("  No export file created (no entries?)")
        print()
        
        # 3. Test safe prune (dry run)
        print("🔄 Testing Safe Prune (DRY RUN)")
        print("-" * 40)
        
        # Temporarily enable dry run
        original_dry_run = retention_manager.config.dry_run
        retention_manager.config.dry_run = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            exported, deleted = await retention_manager.safe_prune_audit_entries(
                session, tmpdir, preserve_checkpoints=True
            )
            print(f"  Exported: {exported}")
            print(f"  Deleted: {deleted} (dry run, should be 0)")
        
        retention_manager.config.dry_run = original_dry_run
        print()
        
        # 4. Final integrity check
        print("🔗 Final Integrity Check")
        print("-" * 40)
        
        final_report = await retention_manager.verify_audit_integrity(session)
        
        if final_report['is_valid']:
            print("  ✅ Audit chain integrity MAINTAINED after retention test")
        else:
            print("  ❌ Audit chain integrity BROKEN!")
            for v in final_report['violations'][:5]:
                print(f"    - {v}")
        print()
    
    await engine.dispose()
    
    # Return exit code
    if report['is_valid'] and final_report['is_valid']:
        print("=" * 60)
        print("✅ RETENTION INTEGRITY TEST PASSED".center(60))
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("❌ RETENTION INTEGRITY TEST FAILED".center(60))
        print("=" * 60)
        return 2


def main() -> int:
    db_url = os.getenv("DATABASE_URL") or os.getenv("WINGMAN_DATABASE_URL")
    
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return 1
    
    if "asyncpg" not in db_url:
        print("ERROR: Must use asyncpg driver")
        return 1
    
    return asyncio.run(test_retention(db_url))


if __name__ == "__main__":
    sys.exit(main())
