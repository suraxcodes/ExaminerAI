import os
import sys
import time
from src.mainPipeline import main

def run_loop(iterations=3):
    print("==================================================")
    print(f"🔄 EXAMER AI STABILITY LOOP TEST ({iterations} iterations)")
    print("==================================================")
    
    # Create test input
    import os
    from pathlib import Path
    test_file = "tests/temp_test_data/clean_textbook.txt"
    Path("tests/temp_test_data").mkdir(parents=True, exist_ok=True)
    with open(test_file, "w") as f:
        f.write("# Chapter 1: Introduction\n\nContent about AI.\n\n# Chapter 2: Ethics\n\nMore content.\n\n" * 20)

    success_count = 0
    
    for i in range(1, iterations + 1):
        print(f"\n▶ RUN {i}/{iterations}")
        start_time = time.time()
        
        # Override args for each run
        sys.argv = ["mainPipeline.py", "--input", test_file, "--output", "OutputData_Loop", "--study-time", "2h"]
        
        try:
            main()
            elapsed = time.time() - start_time
            print(f"\n✅ RUN {i} COMPLETED in {elapsed:.2f} seconds.")
            success_count += 1
        except Exception as e:
            print(f"\n❌ RUN {i} FAILED: {e}")
            
    print("==================================================")
    print(f"🏁 LOOP TEST FINISHED. Success: {success_count}/{iterations}")
    print("==================================================")

if __name__ == "__main__":
    run_loop(3)
