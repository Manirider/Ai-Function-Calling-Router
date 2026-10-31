import json, os
path = r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl'
cases = []
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            cases.append(json.loads(line))
# add two more
extra = [
    {"id":"c061","request":"Find flight from X to Y on 2025-10-10","expected_tool":"FlightSearch","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{"origin":"X","destination":"Y","date":"2025-10-10"}},
    {"id":"c062","request":"Weather in Oslo in F","expected_tool":"WeatherLookup","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{"location":"Oslo","unit":"F"}}
]
cases.extend(extra)
with open(path,'w',encoding='utf-8') as f:
    for c in cases:
        f.write(json.dumps(c)+"\n")
print(len(cases))
