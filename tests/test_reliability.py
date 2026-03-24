import unittest
import os
import shutil
from pathlib import Path
from src.mainPipeline import main

class TestPipelineReliability(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_test_data")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = Path("tests/temp_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # shutil.rmtree(self.test_dir)
        # shutil.rmtree(self.output_dir)
        pass

    def test_clean_textbook_flow(self):
        # Create a mock textbook
        path = self.test_dir / "clean_textbook.txt"
        with open(path, "w") as f:
            f.write("# Chapter 1: Introduction\n\nContent about AI.\n\n# Chapter 2: Ethics\n\nMore content.")
        
        # Run pipeline
        import sys
        sys.argv = ["mainPipeline.py", "--input", str(path), "--output", str(self.output_dir)]
        try:
            main()
            self.assertTrue((self.output_dir / "predicted_exam_v3.json").exists())
        except Exception as e:
            self.fail(f"Pipeline failed on clean textbook: {e}")

    def test_no_past_paper_flow(self):
        import sys
        path = self.test_dir / "no_past_paper.txt"
        with open(path, "w") as f:
            f.write("Lots of content for a single topic. " * 50)
        
        sys.argv = ["mainPipeline.py", "--input", str(path), "--output", str(self.output_dir)]
        try:
            main()
            self.assertTrue((self.output_dir / "predicted_exam_v3.json").exists())
        except Exception as e:
            self.fail(f"Pipeline failed without past paper: {e}")

    def test_prediction_correctness(self):
        import json
        import sys
        path = self.test_dir / "correctness_test.txt"
        with open(path, "w") as f:
            f.write("# Topic: Networking\n\nThe Open Systems Interconnection (OSI) model is a conceptual framework...\n\n")
            f.write("Some unrelated noise over here " * 50)
            
        sys.argv = ["mainPipeline.py", "--input", str(path), "--output", str(self.output_dir)]
        try:
            main()
            output_file = self.output_dir / "predicted_exam_v3.json"
            self.assertTrue(output_file.exists())
            with open(output_file, "r") as f:
                data = json.load(f)
            
            topics = [item["topic"].lower() for item in data]
            osi_found = any("osi" in t for t in topics)
            self.assertTrue(osi_found, f"Expected 'OSI' in predicted topics, got: {topics}")
        except Exception as e:
            self.fail(f"Pipeline failed on prediction correctness: {e}")

if __name__ == "__main__":
    unittest.main()
