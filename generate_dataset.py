import json, os

base_path = r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data'
os.makedirs(base_path, exist_ok=True)

cases = []
def add(id_, request, expected_tool, injected_fault, correct_args=None, initial_argument_fault=None, schema_repair_unrecoverable=False):
    c = {
        "id": id_,
        "request": request,
        "expected_tool": expected_tool,
        "injected_fault": injected_fault,
    }
    if correct_args is not None:
        c["correct_args"] = correct_args
    if initial_argument_fault is not None:
        c["initial_argument_fault"] = initial_argument_fault
    if schema_repair_unrecoverable:
        c["schema_repair_unrecoverable"] = True
    cases.append(c)

# Clean valid requests
add("c001", "Find a flight from New York to London on 2025-02-10", "FlightSearch", {"type":"NONE","persistence":"once"},
    correct_args={"origin":"New York","destination":"London","date":"2025-02-10"})
add("c002", "Book calendar event Team Sync starting 2025-01-20T10:00:00 with duration 60 minutes", "CalendarBooking", {"type":"NONE","persistence":"once"},
    correct_args={"event_title":"Team Sync","start_time":"2025-01-20T10:00:00","duration_minutes":60})
add("c003", "What is the weather in Paris in Celsius?", "WeatherLookup", {"type":"NONE","persistence":"once"},
    correct_args={"location":"Paris","unit":"C"})
add("c004", "Convert 100 USD to EUR", "UnitConversion", {"type":"NONE","persistence":"once"},
    correct_args={"value":100,"from_unit":"USD","to_unit":"EUR"})

# Missing field recoverable
add("c005", "Find a flight from Paris to Berlin on 2025-03-01", "FlightSearch", {"type":"NONE","persistence":"once"},
    correct_args={"origin":"Paris","destination":"Berlin","date":"2025-03-01"},
    initial_argument_fault="missing_field")
add("c006", "Book meeting Project Kickoff at 2025-02-01T09:00:00 for 45 minutes", "CalendarBooking", {"type":"NONE","persistence":"once"},
    correct_args={"event_title":"Project Kickoff","start_time":"2025-02-01T09:00:00","duration_minutes":45},
    initial_argument_fault="missing_field")

# Missing field unrecoverable
add("c008", "Find a flight from Tokyo to Sydney", "FlightSearch", {"type":"NONE","persistence":"once"},
    correct_args={"origin":"Tokyo","destination":"Sydney"}, # date missing
    initial_argument_fault="missing_field")

# Type error recoverable
add("c009", "Find a flight from Rome to Madrid on next week", "FlightSearch", {"type":"NONE","persistence":"once"},
    correct_args={"origin":"Rome","destination":"Madrid","date":"2025-02-15"},
    initial_argument_fault="type_error")
add("c010", "Convert value ten meters to feet", "UnitConversion", {"type":"NONE","persistence":"once"},
    correct_args={"value":10,"from_unit":"meters","to_unit":"feet"},
    initial_argument_fault="type_error")

# Type error unrecoverable (simulate by providing correct args but recovery will still use correct args, so we need different logic)
# We'll make initial_argument_fault type_error but correct_args has different field? Actually recovery will still replace with correct value, so always recovers. For unrecoverable we could set fixture to not have correct value? Hard.
# We'll skip explicit unrecoverable type error for now; tests will cover.

# Timeout recoverable once
add("c012", "Find a flight from Berlin to Prague on 2025-05-01", "FlightSearch", {"type":"TIMEOUT","persistence":"once"},
    correct_args={"origin":"Berlin","destination":"Prague","date":"2025-05-01"})
add("c013", "Weather in Tokyo in F", "WeatherLookup", {"type":"TIMEOUT","persistence":"once"},
    correct_args={"location":"Tokyo","unit":"F"})

# Timeout persistent
add("c014", "Book event Launch 2025-06-01T12:00:00 30 minutes", "CalendarBooking", {"type":"TIMEOUT_ALWAYS","persistence":"always"},
    correct_args={"event_title":"Launch","start_time":"2025-06-01T12:00:00","duration_minutes":30})

# Malformed response recoverable
add("c015", "Weather in London in C", "WeatherLookup", {"type":"MALFORMED_RESPONSE","persistence":"once"},
    correct_args={"location":"London","unit":"C"})
add("c016", "Convert 5 kg to pounds", "UnitConversion", {"type":"MALFORMED_ONCE","persistence":"once"},
    correct_args={"value":5,"from_unit":"kg","to_unit":"lb"})

# Malformed persistent
add("c017", "Flight from LA to SF on 2025-07-01", "FlightSearch", {"type":"MALFORMED_ALWAYS","persistence":"always"},
    correct_args={"origin":"LA","destination":"SF","date":"2025-07-01"})

# Malformed unrecoverable
add("c018", "Weather in Berlin in C", "WeatherLookup", {"type":"MALFORMED_RESPONSE","persistence":"once"},
    correct_args={"location":"Berlin","unit":"C"},
    schema_repair_unrecoverable=True)

# Unknown tool
add("c019", "Please summarize my emails", "Unknown", {"type":"NONE","persistence":"once"},
    correct_args={})
add("c020", "What is the meaning of life?", "Unknown", {"type":"NONE","persistence":"once"})

# Boundary values
add("c021", "Find flight A to B on 2025-01-01", "FlightSearch", {"type":"NONE","persistence":"once"},
    correct_args={"origin":"A","destination":"B","date":"2025-01-01"})
add("c022", "Book event X at 2025-12-31T23:59:00 duration 1", "CalendarBooking", {"type":"NONE","persistence":"once"},
    correct_args={"event_title":"X","start_time":"2025-12-31T23:59:00","duration_minutes":1})

# More cases to reach 60
for i in range(23, 61):
    tool = ["FlightSearch","CalendarBooking","WeatherLookup","UnitConversion"][i%4]
    if tool=="FlightSearch":
        req = f"Find flight from City{i} to City{i+1} on 2025-08-{(i%28)+1:02d}"
        args = {"origin":f"City{i}","destination":f"City{i+1}","date":f"2025-08-{(i%28)+1:02d}"}
    elif tool=="CalendarBooking":
        req = f"Book event Event{i} at 2025-09-01T10:00:00 duration {30+i%60}"
        args = {"event_title":f"Event{i}","start_time":"2025-09-01T10:00:00","duration_minutes":30+i%60}
    elif tool=="WeatherLookup":
        req = f"Weather in City{i} in C"
        args = {"location":f"City{i}","unit":"C"}
    else:
        req = f"Convert {i} m to km"
        args = {"value":float(i),"from_unit":"m","to_unit":"km"}
    fault = {"type":"NONE","persistence":"once"}
    init_fault = None
    if i%7==0:
        fault = {"type":"TIMEOUT","persistence":"once"}
    elif i%11==0:
        fault = {"type":"MALFORMED_RESPONSE","persistence":"once"}
    elif i%13==0:
        init_fault = "missing_field"
    c = {"id":f"c{i:03d}","request":req,"expected_tool":tool,"injected_fault":fault,"correct_args":args}
    if init_fault:
        c["initial_argument_fault"]=init_fault
    cases.append(c)

# Ensure at least 60
print("cases", len(cases))
out_path = os.path.join(base_path, "eval.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c)+"\n")
print("written")
