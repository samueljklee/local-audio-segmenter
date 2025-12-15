# Test Coverage and Guidelines

This document outlines the testing coverage, guidelines, and best practices for the audio auto-segmentation project.

## Current Test Coverage

### Test Distribution (Testing Pyramid)

Our test strategy follows the 60/30/10 testing pyramid principle:

- **Unit Tests (60%)**: Fast, isolated tests for individual components
- **Integration Tests (30%)**: Tests for component interactions
- **End-to-End Tests (10%)**: Complete workflow tests

### Coverage Metrics

- **Target Coverage**: ≥ 90% overall
- **Unit Test Coverage**: ≥ 95%
- **Integration Test Coverage**: ≥ 80%
- **Critical Path Coverage**: 100%

### Test Categories

#### Unit Tests (`tests/unit/`)
- **Configuration System**: (`test_config/`)
  - `test_validator.py`: Configuration validation logic
  - `test_settings.py`: Configuration management
  - `test_defaults.py`: Default configuration values
- **Audio Processing**: (`test_audio/`)
  - `test_loader.py`: Audio file loading functionality
- **Detection Algorithms**: (`test_detection/`)
  - `test_silence_detector.py`: Silence-based detection
  - `test_voice_activity.py`: Voice activity detection
  - `test_spectral_analysis.py`: Spectral change detection
  - `test_energy_detector.py`: Energy-based detection
- **Utilities**: (`test_utils/`)
  - Audio processing utilities
  - Data transformation functions

#### Integration Tests (`tests/integration/`)
- **Pipeline Integration**: (`test_pipeline/`)
  - `test_segmentation_pipeline.py`: Complete workflow testing
- **File I/O**: (`test_fileio/`)
  - Multiple format support
  - Batch processing
- **External Libraries**: (`test_external_libs/`)
  - Librosa integration
  - PyDub integration
  - NumPy/SciPy operations

#### End-to-End Tests (`tests/e2e/`)
- **CLI Interface**: (`test_cli/`)
  - `test_main_cli.py`: Command-line interface testing
- **Performance**: (`test_performance/`)
  - `test_benchmarks.py`: Performance benchmarks
- **Workflows**: (`test_workflows/`)
  - Real-world usage scenarios

## Testing Guidelines

### Test Naming Conventions

- **Test Files**: `test_<module_name>.py`
- **Test Classes**: `Test<ClassName>` (PascalCase)
- **Test Methods**: `test_<functionality>_with_<condition>` (snake_case)

Examples:
```python
class TestSilenceDetector:
    def test_detect_silence_with_mixed_audio(self):
        pass

    def test_detect_silence_empty_audio_raises_error(self):
        pass
```

### Test Structure

Each test should follow the **Arrange-Act-Assert** pattern:

```python
def test_silence_detection_with_threshold_override(self):
    # Arrange
    detector = SilenceDetector(threshold_db=-30.0)
    audio_data = create_test_audio_with_silence()

    # Act
    silent_segments = detector.detect_silence(audio_data, sample_rate=44100)

    # Assert
    assert len(silent_segments) > 0
    assert all(end - start >= 0.1 for start, end in silent_segments)
```

### Test Fixtures

Use fixtures for common test data and setup:

```python
@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing."""
    return {
        'data': np.random.randn(44100),
        'sample_rate': 44100,
        'duration': 1.0,
    }

def test_with_fixture(self, sample_audio_data):
    audio = sample_audio_data['data']
    assert len(audio) == 44100
```

### Mocking Guidelines

- Mock external dependencies (files, network, databases)
- Use `unittest.mock` for Python objects
- Patch at the appropriate level (avoid over-mocking)

```python
def test_audio_loading_with_mock(self, mock_audio_file):
    with patch('src.audio.loader.librosa.load') as mock_load:
        mock_load.return_value = (test_audio_data, 44100)

        loader = AudioLoader()
        audio_data, sample_rate = loader.load_audio(mock_audio_file)

        assert len(audio_data) > 0
        mock_load.assert_called_once()
```

### Error Testing

Test both happy paths and error conditions:

```python
def test_load_audio_invalid_format_raises_error(self):
    with pytest.raises(AudioLoadError, match="Unsupported audio format"):
        self.loader.load_audio("invalid_format.xyz")

def test_config_validation_invalid_threshold(self):
    with pytest.raises(ConfigValidationError) as exc_info:
        self.config.set("segmentation.silence_threshold", -100)

    assert "silence_threshold must be between -60 and 0" in str(exc_info.value)
```

### Property-Based Testing

Use property-based testing for algorithms with input validation:

```python
@given(st.lists(st.floats(min_value=-1.0, max_value=1.0), min_size=100, max_size=10000))
def test_audio_normalization_preserves_shape(self, audio_samples):
    audio_data = np.array(audio_samples)
    normalized = normalize_audio(audio_data)

    assert normalized.shape == audio_data.shape
    assert np.all(np.abs(normalized) <= 1.0)
```

## Performance Testing

### Benchmark Categories

1. **Loading Benchmarks**: Audio file loading performance
2. **Processing Benchmarks**: Algorithm performance on different input sizes
3. **Memory Benchmarks**: Memory usage patterns
4. **Scalability Tests**: Performance with increasing data sizes

### Benchmark Structure

```python
@pytest.mark.benchmark
def test_silence_detection_performance(self, benchmark):
    audio_data = generate_large_audio_data()

    def detect_silence():
        return self.detector.detect_silence(audio_data, 44100)

    result = benchmark(detect_silence)
    assert isinstance(result, list)
```

### Performance Thresholds

- **Loading Speed**: ≥ Real-time (1x processing)
- **Memory Usage**: ≤ 100MB for 1-minute audio
- **Startup Time**: ≤ 2 seconds for CLI initialization

## Continuous Integration

### CI Pipeline

1. **Linting**: Code style and quality checks
2. **Type Checking**: Static type analysis
3. **Unit Tests**: Fast feedback on core functionality
4. **Integration Tests**: Component interaction validation
5. **End-to-End Tests**: Complete workflow validation
6. **Performance Tests**: Regression detection
7. **Security Scans**: Dependency vulnerability checks

### Test Matrix

- **Python Versions**: 3.8, 3.9, 3.10, 3.11
- **Operating Systems**: Linux, macOS, Windows
- **Dependencies**: Minimum and latest versions

## Quality Gates

### Pre-commit Checks

```bash
# Run all quality checks
pre-commit run --all-files

# Individual checks
black src tests
flake8 src tests
mypy src
pytest tests/unit
```

### Coverage Requirements

- **Overall Coverage**: ≥ 90%
- **New Code Coverage**: ≥ 95%
- **Critical Components**: 100% coverage

### Performance Regression

- **Benchmark Degradation**: < 10% slowdown
- **Memory Increase**: < 20% growth
- **Startup Time**: < 5 second increase

## Test Data Management

### Fixtures Organization

```
tests/fixtures/
├── audio_samples/          # Test audio files
│   ├── short_wav.wav
│   ├── stereo_audio.wav
│   └── large_audio.wav
├── configs/               # Test configuration files
│   ├── valid_config.json
│   ├── invalid_config.yaml
│   └── edge_case_config.json
└── expected_outputs/      # Expected test results
    ├── segmentation_results.json
    └── processed_audio.wav
```

### Test Data Guidelines

- Keep test files small and focused
- Use deterministic test data when possible
- Include edge cases in test fixtures
- Clean up temporary files after tests

## Debugging Tests

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_audio/test_loader.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run with debugging
pytest -v -s --pdb

# Run performance tests
pytest tests/performance --benchmark-only
```

### Common Issues

1. **Flaky Tests**: Tests that pass/fail intermittently
   - Add retry mechanisms for external dependencies
   - Use deterministic test data
   - Avoid timing-based assertions

2. **Slow Tests**: Tests that take too long
   - Mock expensive operations
   - Use smaller test datasets
   - Mark slow tests with `@pytest.mark.slow`

3. **Memory Leaks**: Tests that don't clean up properly
   - Use proper teardown in fixtures
   - Monitor memory usage in performance tests
   - Explicitly delete large objects

## Best Practices

### Test Design

1. **Single Responsibility**: Each test should verify one behavior
2. **Independence**: Tests should not depend on each other
3. **Repeatability**: Tests should produce the same results every time
4. **Clear Assertions**: Use descriptive assertion messages
5. **Edge Cases**: Test boundary conditions and error scenarios

### Code Coverage

1. **Focus on Critical Paths**: Prioritize testing important functionality
2. **Avoid Meaningless Coverage**: Don't test getters/setters or trivial code
3. **Test Error Paths**: Ensure error handling is properly tested
4. **Integration Points**: Test interactions between components

### Maintenance

1. **Regular Updates**: Keep tests updated with code changes
2. **Review Test Failures**: Investigate and fix test failures promptly
3. **Refactor Tests**: Improve test code quality and readability
4. **Documentation**: Keep test documentation current

## Tools and Resources

### Testing Tools

- **pytest**: Primary testing framework
- **pytest-cov**: Coverage measurement
- **pytest-mock**: Mocking capabilities
- **pytest-benchmark**: Performance testing
- **pytest-xdist**: Parallel test execution

### Quality Tools

- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning
- **safety**: Dependency vulnerability checking

### Documentation

- **pytest documentation**: https://docs.pytest.org/
- **test coverage guidelines**: Internal team wiki
- **CI/CD pipeline**: GitHub Actions configuration

This comprehensive test strategy ensures high-quality, maintainable code while catching issues early in the development process.