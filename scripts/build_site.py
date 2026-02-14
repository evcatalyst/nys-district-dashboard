#!/usr/bin/env python3
"""
Build static site for GitHub Pages.

Copies site/ files to out/ and generates manifest.json with SHA256 hashes.
"""

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
SITE_DIR = Path("site")
OUT_DIR = Path("out")
CONFIG_DIR = Path("config")


class SiteBuilder:
    """Build static site and manifest."""

    def __init__(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        self.manifest: Dict[str, str] = {}

    def compute_sha256(self, filepath: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def copy_site_files(self):
        """Copy site files to out directory."""
        if not SITE_DIR.exists():
            logger.error(f"Site directory not found: {SITE_DIR}")
            return
        
        # Copy all files from site/ to out/
        for item in SITE_DIR.iterdir():
            if item.is_file():
                dest = OUT_DIR / item.name
                shutil.copy2(item, dest)
                logger.info(f"Copied {item.name} to out/")
            elif item.is_dir():
                dest = OUT_DIR / item.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                logger.info(f"Copied directory {item.name}/ to out/")

    def generate_manifest(self):
        """Generate manifest.json with SHA256 hashes of all files."""
        logger.info("Generating manifest.json...")
        
        # Walk through all files in out/
        for filepath in OUT_DIR.rglob('*'):
            if filepath.is_file() and filepath.name != 'manifest.json':
                relative_path = filepath.relative_to(OUT_DIR)
                sha256 = self.compute_sha256(filepath)
                self.manifest[str(relative_path)] = sha256
        
        # Save manifest
        manifest_file = OUT_DIR / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2, sort_keys=True)
        
        logger.info(f"Generated manifest with {len(self.manifest)} files")

    def build_resources(self):
        """Merge config/resources.json with BOCES info and write to out/data/resources.json."""
        resources_cfg = CONFIG_DIR / "resources.json"
        districts_cfg = CONFIG_DIR / "districts.json"
        if not resources_cfg.exists():
            logger.warning("config/resources.json not found, skipping resources build")
            return

        with open(resources_cfg) as f:
            resources = json.load(f)
        boces_map: Dict[str, str] = {}
        if districts_cfg.exists():
            with open(districts_cfg) as f:
                for d in json.load(f):
                    boces_map[d["name"]] = d.get("boces", "")

        for entry in resources:
            entry.setdefault("boces", boces_map.get(entry["name"], ""))

        data_dir = OUT_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dest = data_dir / "resources.json"
        with open(dest, "w") as f:
            json.dump(resources, f, indent=2)
        logger.info("Generated out/data/resources.json with %d districts", len(resources))

    def build(self):
        """Run the full build process."""
        logger.info("Building static site...")
        
        # Copy site files
        self.copy_site_files()

        # Build resources data
        self.build_resources()
        
        # Generate manifest
        self.generate_manifest()
        
        logger.info("\nSite build complete!")
        logger.info(f"Output directory: {OUT_DIR.absolute()}")


def main():
    """Main entry point."""
    builder = SiteBuilder()
    builder.build()
    
    return 0


if __name__ == "__main__":
    exit(main())
