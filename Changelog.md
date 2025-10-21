# Changelog

All notable changes to AutoFix Python Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🔮 Planned for v2.8.0
- Complete Clean Architecture migration
- AI provider abstraction layer
- Handler migration to new structure
- Enhanced documentation with diagrams

---

## [2.7.0-beta] - 2025-10-21

### 🎉 Major Release: Clean Architecture + Quality Analysis

### Added
- **Clean Architecture Foundation**
  - Domain layer with entities, value objects, and exceptions
  - Application layer with interfaces (AnalyzerInterface, AIServiceInterface, HandlerInterface)
  - Infrastructure layer for concrete implementations
  - Dependency inversion principle throughout

- **BanditAnalyzer - Security Scanner**
  - 30+ security vulnerability checks
  - Detects hardcoded secrets, SQL injection, command injection
  - SSL/TLS issues, weak cryptography detection
  - Comprehensive security reporting with severity levels

- **RadonAnalyzer - Complexity Metrics**
  - Maintainability Index (MI) scoring (-50 to 100 scale)
  - Cyclomatic Complexity (CC) analysis
  - Grade assignment (A through F)
  - Per-function complexity reporting

- **Quality API Endpoints**
  - `GET /api/v1/quality/analyzers` - List available analyzers
  - `GET /api/v1/quality/health` - Health check for analyzers
  - `GET /api/v1/quality/stats` - Detailed statistics
  - `POST /api/v1/quality/security` - Run Bandit security scan
  - `POST /api/v1/quality/complexity` - Run Radon complexity analysis

- **Enhanced Error Handling**
  - Improved error messages with installation hints
  - Service unavailable (503) for missing dependencies
  - Better request validation with Pydantic v2

### Changed
- **PylintAnalyzer Migration**
  - Moved to `autofix_core.infrastructure.analyzers`
  - Implements AnalyzerInterface
  - Backward compatibility shims in old location
  - Updated all imports and tests

- **API Structure**
  - Better separation of concerns
  - Consistent response models
  - Enhanced Swagger documentation

### Fixed
- Negative Maintainability Index validation (now allows -50 to 100 range)
- Test compatibility with new architecture
- Mock objects in test suite for new structure

### Tests
- Total: 169 tests passing ✅
- New: 11 tests for Bandit and Radon
- Updated: PylintAnalyzer tests for new structure
- Coverage maintained at 85%+

### Performance
- Security scans: ~2-3 seconds
- Complexity analysis: ~1-2 seconds
- Health checks: < 100ms

### Architecture
- **Migration Progress: 30%**
  - ✅ Analyzers: 75% complete (3/4)
  - ⏳ AI Providers: 0% complete (GeminiService pending)
  - ⏳ Handlers: 0% complete (20 handlers pending)
  - ⏳ Services: 0% complete

### Credits
- Jules AI: Professional code review and approval
- GitHub Copilot: Implementation assistance
- Amazon Q: Documentation support

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
