#!/usr/bin/env python3
"""
Download Real Tomato Datasets for Training
Supports Kaggle and GitHub datasets
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TomatoDatasetDownloader:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.dataset_dir = storage_dir / "dataset"
        self.images_dir = self.dataset_dir / "images"
        self.annotations_dir = self.dataset_dir / "annotations"
        self.temp_dir = storage_dir / "temp"
        
        # Create directories
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.annotations_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def check_kaggle_cli(self) -> bool:
        """Check if Kaggle CLI is installed"""
        try:
            result = subprocess.run(["kaggle", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def install_kaggle_cli(self) -> bool:
        """Install Kaggle CLI"""
        try:
            logger.info("Installing Kaggle CLI...")
            subprocess.run(["pip", "install", "kaggle"], check=True)
            logger.info("Kaggle CLI installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install Kaggle CLI: {e}")
            return False
    
    def download_laboro_tomato(self) -> Dict[str, any]:
        """Download Laboro Tomato dataset from Kaggle"""
        logger.info("Downloading Laboro Tomato dataset...")
        
        # Check if Kaggle CLI is available
        if not self.check_kaggle_cli():
            logger.warning("Kaggle CLI not found. Installing...")
            if not self.install_kaggle_cli():
                return {
                    "status": "error",
                    "message": "Failed to install Kaggle CLI"
                }
        
        try:
            # Download dataset
            cmd = [
                "kaggle", "datasets", "download", 
                "nexuswho/laboro-tomato",
                "-p", str(self.temp_dir)
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Download failed: {result.stderr}")
                return {
                    "status": "error",
                    "message": f"Download failed: {result.stderr}"
                }
            
            # Extract the downloaded zip
            zip_path = self.temp_dir / "laboro-tomato.zip"
            if zip_path.exists():
                import zipfile
                logger.info("Extracting dataset...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.dataset_dir)
                
                # Organize files
                self._organize_laboro_dataset()
                
                return {
                    "status": "success",
                    "message": "Laboro Tomato dataset downloaded and extracted",
                    "dataset_info": {
                        "name": "laboro-tomato",
                        "images": 804,
                        "classes": 6,
                        "format": "COCO JSON"
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Downloaded file not found"
                }
                
        except Exception as e:
            logger.error(f"Failed to download dataset: {e}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def _organize_laboro_dataset(self):
        """Organize Laboro dataset files"""
        # This would organize the downloaded files into the expected structure
        # For now, it's a placeholder
        logger.info("Organizing dataset files...")
        
        # Find and move images
        for ext in ['*.jpg', '*.png', '*.jpeg']:
            for img_file in self.dataset_dir.rglob(ext):
                try:
                    dest = self.images_dir / img_file.name
                    if not dest.exists():
                        import shutil
                        shutil.copy2(img_file, dest)
                except Exception as e:
                    logger.warning(f"Failed to copy {img_file}: {e}")
        
        # Find and move annotations
        for json_file in self.dataset_dir.rglob("*.json"):
            try:
                dest = self.annotations_dir / json_file.name
                if not dest.exists():
                    import shutil
                    shutil.copy2(json_file, dest)
            except Exception as e:
                logger.warning(f"Failed to copy {json_file}: {e}")
    
    def download_tomatod_github(self) -> Dict[str, any]:
        """Download tomatOD dataset from GitHub"""
        logger.info("Downloading tomatOD dataset from GitHub...")
        
        try:
            import zipfile
            import urllib.request
            
            # Download from GitHub releases
            url = "https://github.com/up2metric/tomatOD/archive/refs/heads/master.zip"
            zip_path = self.temp_dir / "tomatod.zip"
            
            logger.info(f"Downloading from {url}...")
            urllib.request.urlretrieve(url, zip_path)
            
            # Extract
            logger.info("Extracting dataset...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Organize files
            self._organize_tomatod_dataset()
            
            return {
                "status": "success",
                "message": "tomatOD dataset downloaded and extracted",
                "dataset_info": {
                    "name": "tomatOD",
                    "images": 277,
                    "classes": 3,
                    "format": "YOLO"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to download tomatOD: {e}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def _organize_tomatod_dataset(self):
        """Organize tomatOD dataset files"""
        logger.info("Organizing tomatOD dataset files...")
        
        # Find extracted directory
        extracted_dirs = [d for d in self.temp_dir.iterdir() if d.is_dir() and "tomatOD" in d.name.lower()]
        
        if extracted_dirs:
            source_dir = extracted_dirs[0]
            
            # Move images
            for ext in ['*.jpg', '*.png', '*.jpeg']:
                for img_file in source_dir.rglob(ext):
                    try:
                        dest = self.images_dir / img_file.name
                        if not dest.exists():
                            import shutil
                            shutil.copy2(img_file, dest)
                    except Exception as e:
                        logger.warning(f"Failed to copy {img_file}: {e}")
    
    def get_dataset_status(self) -> Dict[str, any]:
        """Get current dataset status"""
        images_count = len(list(self.images_dir.glob("*.jpg"))) + len(list(self.images_dir.glob("*.png")))
        annotations_count = len(list(self.annotations_dir.glob("*.json")))
        
        return {
            "images_count": images_count,
            "annotations_count": annotations_count,
            "dataset_ready": images_count > 0,
            "storage_used": sum(f.stat().st_size for f in self.dataset_dir.rglob("*") if f.is_file()) / (1024 * 1024)  # MB
        }

def main():
    """Main execution"""
    storage_dir = Path(__file__).parent.parent / "storage"
    downloader = TomatoDatasetDownloader(storage_dir)
    
    logger.info("Tomato Dataset Downloader")
    logger.info("=" * 50)
    
    # Check current status
    status = downloader.get_dataset_status()
    logger.info(f"Current dataset status: {status}")
    
    # Download Laboro Tomato dataset (recommended)
    logger.info("\nAttempting to download Laboro Tomato dataset...")
    result = downloader.download_laboro_tomato()
    
    print(json.dumps(result, indent=2))
    
    # Check final status
    final_status = downloader.get_dataset_status()
    logger.info(f"\nFinal dataset status: {final_status}")

if __name__ == "__main__":
    main()
