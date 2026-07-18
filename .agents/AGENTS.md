# MACI Project Rules

- Before implementing business logic that depends on third-party APIs or industry-specific processes (airlines, payments, healthcare, legal), always research and validate the domain constraints first. Flag any discovered constraints to the user BEFORE writing code. Cite specific limitations (e.g., "Airline group bookings require 10+ passengers and proprietary API access").
- Do not blindly implement the user's plan if domain knowledge or research suggests a fundamental flaw. Push back respectfully with evidence. Say "I want to flag a potential issue before we build this" rather than silently proceeding. The user explicitly prefers being challenged over being agreed with.
