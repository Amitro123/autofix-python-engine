# Changelog

All notable changes to AutoFix Python Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.1] - 2025-10-12

### Added
- **Gemini AI Caching System** (Jules recommendation)
  - File-based cache for Gemini responses
  - 30-day TTL with automatic cleanup
  - Cache hit/miss tracking and statistics
  - Reduces API costs and improves response time

- **Accurate Token Counting** (Jules recommendation)
  - Use `model.count_tokens()` for exact counts
  - Prevents InvalidRequestError from token limits
  - Fast and lightweight validation

### Changed
- `GeminiService.fix_with_ai()` now checks cache before API calls
- Added `_count_tokens()` method with official Gemini API
- Enhanced logging with custom log levels (SUCCESS, ATTEMPT)

### Fixed
- Cache initialization bug when disabled
- Token estimation fallback for API failures

### Tests
- Added 6 comprehensive cache tests (all passing)
- Total: 41/41 tests passing

### Performance
- ⚡ Faster response for cached errors
- 💰 Lower API costs through caching
- 🎯 Better token management

### Credits
- Expert code review and recommendations by Jules
- "Top-tier work" feedback on implementation

---

## [2.2.0] - 2025-10-12

### Added
- ✨ **FileNotFoundError Handler** - Comprehensive suggestions for missing file errors
- ✨ **ValueError Handler** - Intelligent type conversion error handling
- 📊 **Comprehensive Example Fixes** - Concrete before/after code examples
- 🧪 **6 New Tests** - Dedicated test suite for new handlers

### Changed
- 📚 Updated documentation (12 supported error types)
- 📊 Enhanced metrics and success rate statistics
- 🔧 Improved architecture with consistent patterns
- 📈 Test coverage increased from 29 to 35 tests

### Improved
- 💡 Better error messages with formatted output
- 📖 Context-aware recommendations
- 🎯 More accurate error detection
- 🎨 Consistent UX across all handlers

### Technical
- Error handler count: 10 → 12 types
- Test count: 29 → 35 tests
- All tests passing: 35/35 ✅

---

## [2.1.0] - 2025-10-10

### Added
- 🤖 **AI-Powered Fixes** - Integrated Google's Gemini 2.5 Pro
- 🚀 **REST API** - Full FastAPI backend with 8 endpoints
- 🎯 **Hybrid Error Fixing** - Smart fallback from AutoFix to Gemini
- 🔐 **Secure API Key Management** - Environment variable support
- 📊 **Enhanced Metrics** - Firebase integration

### Changed
- Version bump: 1.0.0 → 2.1.0
- Architecture: CLI-only → CLI + REST API
- Error handling: Rule-based → Hybrid (Rules + AI)

### Performance
- Simple errors: ~0.6s (AutoFix)
- Complex errors: ~7s (Gemini)
- Combined success rate: 98%+

---

## [1.0.0] - 2025-10-08

### 🎉 Initial Release

First production-ready release of AutoFix Python Engine!

### Features
- ✅ Automatic error detection during execution
- ✅ Auto-fix capabilities for 7 error types
- ✅ Interactive CLI with prompts
- ✅ Firebase integration for metrics
- ✅ Cross-platform support

### Supported Error Types (7)
- SyntaxError, IndentationError, ModuleNotFoundError
- TypeError, IndexError, NameError, TabError

### Testing
- 29 unit tests passing
- Coverage: ~30%

### Performance
- Small files: < 1 second
- Large files: 3-5 seconds

---

## [Unreleased]

### 🔮 Planned for v2.3.0
- More error types (RuntimeError, AssertionError)
- Enhanced CLI formatting
- Configuration file support

### 🚀 Planned for v3.0.0
- Web Interface
- VSCode Extension
- Multi-file support

---

[2.2.1]: https://github.com/Amitro123/autofix-python-engine/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/Amitro123/autofix-python-engine/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Amitro123/autofix-python-engine/compare/v1.0.0...v2.1.0
[1.0.0]: https://github.com/Amitro123/autofix-python-engine/releases/tag/v1.0.0
