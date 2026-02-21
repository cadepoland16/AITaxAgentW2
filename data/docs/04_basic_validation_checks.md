# Basic Validation Checks (Demo)

A W-2 validator can flag:

- Missing required boxes for federal wages/withholding.
- Negative amounts where not expected.
- Box 2 withholding that appears extremely low or high relative to Box 1 (soft warning only).
- Box 3 above annual wage limit for the stated tax year.
- Missing state wages when state withholding is present.

Warnings are triage signals, not final determinations.
