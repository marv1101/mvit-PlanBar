# PlanBar Backend Architektur

Planbar ist eine Applikation für das Management von Schichtplänen für KMUs. Es ermöglicht die automatisierte Erstellung von Schichtplänen über mvit TiTO und bietet über das Frontend eine ansprechende User-Schnittstelle. Das Backend dient als Schnittstelle zwischen Frontend, DB und TiTO.


API-Calls werden vom Frontend abgesetzt und vom Backend angenommen.
Backend wertet Call aus

Jobanforderungen für TiTO werden an den TiTO-Endpunkt /jobs via HTTP Post weitergeleitet.
Usermanagement, Mitarbeiterdaten sowie Ergebnisse von TiTO hält das Backend in einer eigenen DB vor.

## Datenschema

User
- userid
- username (varchar(64))
- role (user/admin)
- email - varchar (regex validated)
- password (encrypted)
- lastlogin - Timestamp
- created - Timestamp

Employee
- employeeid
- userid - foreign key
- contractid - foreign key
- timecardid - foreign key

Contract
- contractid
- weeklyworkinghours
- breaktime
- hiredrole

Timecard
- timecardid
- week
- year
- balance

ShiftWish
- wishid
- emloyeeid - foreign key
- date
- week
- type
- note

Shiftplan
(aus tito Result generiert - als JSON?)
Muss in Frontend anzeigbar sein

TiTO Result in Form:
{"metadata": {"status": "SUCCESS", "solveTimeSeconds": 0.01, "timestamp": "2026-05-08T13:23:27.904019Z"}, "solution": {"assignments": [{"employeeId": "emp_001", "date": "2026-01-02", "shiftId": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}, {"employeeId": "emp_003", "date": "2026-01-02", "shiftId": "S_SPAET", "startTime": "14:00", "endTime": "22:00"}, {"employeeId": "emp_002", "date": "2026-01-03", "shiftId": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}, {"employeeId": "emp_001", "date": "2026-01-04", "shiftId": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}, {"employeeId": "emp_002", "date": "2026-01-05", "shiftId": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}, {"employeeId": "emp_001", "date": "2026-01-05", "shiftId": "S_SPAET", "startTime": "14:00", "endTime": "22:00"}], "unassignedRequirements": []}, "metrics": {"wishFulfillmentRate": 100.0, "totalObjectiveScore": 600, "employeeUtilization": {"emp_001": 24.0, "emp_002": 16.0, "emp_003": 8.0}, "violations": {"softConstraints": []}}, "diagnostics": {"isOptimal": true, "info": "Optimale L\u00f6sung gefunden."}}