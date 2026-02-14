from documentLoader import DocumentsExtractor
    
result = DocumentsExtractor.extract("../dataSet/Fundamentals_of_Cybersecurity.pdf")
print(result.raw_text)

with open("../dataSet/OutputData/output.txt", "w", encoding="utf-8") as f:
    f.write(result.raw_text) 