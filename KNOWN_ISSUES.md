# Known Issues

This document lists the known issues for AutoFix v1.0.0.

## General
- AutoFix is not a static analysis tool and only detects errors at runtime.
- The tool processes errors sequentially and does not handle multiple errors at once.
- AutoFix currently only supports fixing errors in a single file at a time.

## Error Handling
- `IndexError` and `KeyError` fixes require manual review and are not applied automatically.
- Complex nested logic may not be handled correctly in all cases.
- Some `SyntaxError` variations may not be correctly identified and fixed.
- The tool may not be able to fix errors in very large files (over 1000 lines).

## Performance
- There are no known performance issues at this time.

## Security
- There are no known security vulnerabilities at this time.