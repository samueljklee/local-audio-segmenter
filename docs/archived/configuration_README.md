# Configuration System Documentation

The audio auto-segmentation project uses a flexible YAML-based configuration system with JSON Schema validation and domain-specific profiles for different types of audio content.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration Profiles](#configuration-profiles)
- [Semantic Labeling](#semantic-labeling)
- [Configuration Schema](#configuration-schema)
- [CLI Tools](#cli-tools)
- [API Usage](#api-usage)
- [Examples](#examples)

## Quick Start

### Using Pre-built Profiles

```bash
# Use the church service profile
audio-segmenter sermon.wav --profile church_service

# Use the lecture profile
audio-segmenter lecture.mp3 --profile lecture

# Use the podcast profile
audio-segmenter episode.wav --profile podcast
```

### Creating Custom Configuration

```bash
# Create a custom profile based on lecture
config-cli create-profile my_lecture --base-profile lecture --overrides '{"audio":{"sample_rate":48000}}'

# Validate your configuration
config-cli validate-config my_config.yaml

# Show profile information
config-cli profile-info church_service
```

## Configuration Profiles

Pre-built configuration profiles are available for common audio content types:

### Church Service Profile (`church_service`)
- **Optimized for**: Worship services, sermons, religious gatherings
- **Features**:
  - Detects sermons, worship music, prayers, scripture readings
  - Handles applause and intentional silence
  - 44.1kHz mono audio with noise reduction

### Lecture Profile (`lecture`)
- **Optimized for**: Academic lectures, presentations, educational content
- **Features**:
  - Identifies lecture content, Q&A sessions, demonstrations
  - Handles teaching pauses and note-taking time
  - Detects introductions and conclusions

### Podcast Profile (`podcast`)
- **Optimized for**: Podcast episodes, interviews, conversations
- **Features**:
  - Detects intro/outro music, host monologues, interviews
  - Handles advertisements and sponsor segments
  - Stereo audio support with background music detection

### Meeting Profile (`meeting`)
- **Optimized for**: Business meetings, conference calls, discussions
- **Features**:
  - Identifies presentations, discussions, decision-making
  - Handles brainstorming sessions and action items
  - Optimized for multiple speakers

## Semantic Labeling

The semantic labeling system automatically categorizes audio segments based on audio characteristics and content patterns.

### Configuration Structure

```yaml
semantic_labeling:
  enabled: true

  categories:
    sermon:
      description: "Main sermon or homily portion"
      color: "#2E86AB"
      icon: "microphone"
      min_duration: 300

    worship_music:
      description: "Musical worship and songs"
      color: "#A23B72"
      icon: "music"
      min_duration: 60

  rules:
    - name: "detect_sermon_start"
      label: "sermon"
      priority: 9
      confidence_threshold: 0.7
      pattern:
        min_duration: 300
        silence_threshold: -35
        energy_range:
          min: 0.1
          max: 0.8
        spectral_features:
          centroid_range:
            min: 1000
            max: 3000
```

### Semantic Categories

Each category defines:
- **description**: Human-readable description
- **color**: Color code for visualization
- **icon**: Icon identifier for UI
- **min_duration**: Minimum duration for validity
- **merge_with**: Categories to merge this with

### Semantic Rules

Rules define patterns that trigger semantic labels:
- **name**: Rule identifier
- **label**: Semantic label to apply
- **priority**: Rule importance (1-10, higher = more important)
- **confidence_threshold**: Minimum confidence for application
- **pattern**: Audio characteristics to match

#### Pattern Matching

Pattern matching uses multiple audio features:

```yaml
pattern:
  # Duration constraints
  min_duration: 300  # seconds
  max_duration: 1800  # seconds

  # Audio level features
  silence_threshold: -35  # dB
  energy_range:
    min: 0.1  # normalized energy
    max: 0.8

  # Spectral features
  spectral_features:
    centroid_range:
      min: 1000  # Hz
      max: 3000  # Hz
    rolloff_range:
      min: 2000  # Hz
      max: 5000  # Hz

  # Position-based matching
  position: "start"  # "start", "end", or omit for any position
```

## Configuration Schema

The complete configuration follows this structure:

### Root Configuration

```yaml
# Profile identifier
profile: "church_service"  # Optional: predefined profile name

# Domain configuration
domain:
  type: "speech"           # speech, music, mixed, ambient
  language: "en"          # ISO 639-1 language code
  characteristics:
    - formal_speech
    - sermon
    - music_background

# Semantic labeling (see above)
semantic_labeling:
  enabled: true
  # ... semantic labeling config

# Audio processing
audio:
  sample_rate: 44100      # 8kHz to 96kHz
  bit_depth: 16          # 8, 16, 24, or 32
  channels: 1            # 1 (mono) or 2 (stereo)
  format: "wav"          # wav, mp3, flac, ogg, m4a, aac
  normalize: true        # Audio normalization
  trim_silence: true     # Remove leading/trailing silence
  preprocessing:
    high_pass_filter:
      enabled: true
      cutoff: 80         # Hz
    noise_reduction:
      enabled: true
      strength: 0.3      # 0.0 to 1.0

# Segmentation parameters
segmentation:
  method: "semantic"     # silence, voice_activity, spectral, energy, hybrid, semantic
  min_segment_length: 5.0   # seconds
  max_segment_length: 300.0 # seconds
  silence_threshold: -40     # dB
  silence_padding: 0.3       # seconds
  vad_aggressiveness: 2      # 0-3 scale
  energy_threshold: 0.05     # normalized
  spectral_threshold: 0.12   # normalized
  hybrid_weights:           # For hybrid method
    silence_weight: 0.4
    energy_weight: 0.3
    spectral_weight: 0.2
    vad_weight: 0.1

# Output configuration
output:
  format: "wav"          # Output audio format
  sample_rate: null      # Use input rate if null
  bit_depth: 16
  quality: "high"        # low, medium, high
  naming_scheme: "semantic" # sequential, timestamp, semantic, hash
  metadata: true
  segments_file:
    enabled: true
    format: "json"       # json, csv, txt, srt, vtt, xml
    include_semantic_labels: true
    include_confidence_scores: true
    include_audio_features: false
  visualization:
    enabled: true
    format: "png"        # png, svg, pdf
    waveform: true
    spectrogram: true
    segments_overlay: true
    semantic_colors: true

# Performance settings
performance:
  batch_size: 32         # Processing batch size
  num_workers: 4         # Parallel workers
  memory_limit: 1024     # MB
  use_gpu: false         # GPU acceleration
  chunk_size: 8192       # Audio chunk size

# Logging
logging:
  level: "INFO"          # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: null             # Log file path or null for stdout
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  verbose: false
```

## CLI Tools

### Configuration Management CLI (`config-cli`)

```bash
# List available profiles
config-cli list-profiles

# Show profile information
config-cli profile-info church_service

# Validate configuration
config-cli validate-config my_config.yaml

# Create custom profile
config-cli create-profile my_profile --base-profile lecture --overrides '{"audio":{"sample_rate":48000}}'

# Show configuration
config-cli show-config --profile church_service --format json

# Merge configurations
config-cli merge-configs --profile base_config.yaml additional.yaml --output merged.yaml

# Test profile with audio
config-cli test-profile lecture --audio sample.wav
```

### Main CLI with Profile Support

```bash
# Use profile with main CLI
audio-segmenter sermon.wav --profile church_service

# Combine profile with custom overrides
audio-segmenter lecture.wav --profile lecture --threshold -35 --min-length 10

# Save profile-based configuration
audio-segmenter episode.wav --profile podcast --save-config my_podcast_config.yaml
```

## API Usage

### Basic Configuration Loading

```python
from src.config.settings import ConfigManager

# Load with profile
config = ConfigManager(profile="church_service")

# Load with config file
config = ConfigManager(config_path="my_config.yaml")

# Load with both (profile first, then config overrides)
config = ConfigManager(config_path="custom.yaml", profile="lecture")
```

### Working with Profiles

```python
from src.config.profile_loader import ProfileLoader

loader = ProfileLoader()

# List profiles
profiles = loader.list_profiles()
print(f"Available profiles: {profiles}")

# Get profile information
info = loader.get_profile_info("church_service")
print(f"Profile type: {info['domain']['type']}")

# Create custom profile
custom_config = loader.create_custom_profile(
    "my_church",
    "church_service",
    {"audio": {"sample_rate": 48000}}
)

# Save profile
loader.save_profile("my_church", custom_config)
```

### Semantic Labeling Access

```python
from src.config.settings import ConfigManager

config = ConfigManager(profile="church_service")

# Check if semantic labeling is enabled
if config.is_semantic_labeling_enabled:
    print("Semantic labeling is enabled")

    # Get categories
    categories = config.semantic_categories
    for name, category in categories.items():
        print(f"Category '{name}': {category['description']}")

    # Get rules for a specific label
    sermon_rules = config.get_semantic_rules_for_label("sermon")
    print(f"Found {len(sermon_rules)} rules for sermon detection")

    # Get specific category
    sermon_category = config.get_semantic_category("sermon")
    print(f"Sermon color: {sermon_category.get('color')}")
```

### Configuration Management

```python
# Get configuration values
sample_rate = config.get("audio.sample_rate")
threshold = config.get("segmentation.silence_threshold", -40)

# Set configuration values (with validation)
config.set("segmentation.min_segment_length", 10.0)

# Get entire sections
audio_config = config.audio_config
segmentation_config = config.segmentation_config

# Save configuration
config.save_config("output_config.yaml")

# Validate external configuration
try:
    config.load_config_dict({"audio": {"sample_rate": 48000}})
    print("Configuration is valid")
except ConfigValidationError as e:
    print(f"Invalid configuration: {e}")
```

## Examples

### Example 1: Church Service Processing

```bash
# Process sermon with church service profile
audio-segmenter sermon_2024_01_07.wav \
  --profile church_service \
  --output processed_sermons/ \
  --format wav \
  --save-config sermon_config.yaml
```

```yaml
# sermon_config.yaml (auto-generated)
profile: church_service
audio:
  sample_rate: 44100
  channels: 1
  normalize: true
segmentation:
  method: semantic
  silence_threshold: -40
output:
  format: wav
  naming_scheme: semantic
  segments_file:
    enabled: true
    include_semantic_labels: true
```

### Example 2: Custom Lecture Profile

```python
from src.config.settings import ConfigManager

# Create enhanced lecture profile
config = ConfigManager(profile="lecture")

# Add custom preprocessing for classroom audio
config.set("audio.preprocessing.noise_reduction.strength", 0.5)
config.set("audio.preprocessing.high_pass_filter.cutoff", 100)

# Adjust segmentation for longer lectures
config.set("segmentation.max_segment_length", 600)  # 10 minutes
config.set("segmentation.min_segment_length", 30)   # 30 seconds

# Add custom semantic category
config.set("semantic_labeling.categories.student_question", {
    "description": "Student questions from audience",
    "color": "#FF9800",
    "min_duration": 5
})

# Save custom profile
config.save_profile("enhanced_lecture")

# Use the custom profile
# audio-segmenter lecture.wav --profile enhanced_lecture
```

### Example 3: Podcast Production Workflow

```bash
# 1. Create podcast-specific profile
config-cli create-profile podcast_production \
  --base-profile podcast \
  --overrides '{
    "audio": {
      "sample_rate": 48000,
      "bit_depth": 24,
      "channels": 2,
      "preprocessing": {
        "noise_reduction": {"enabled": true, "strength": 0.2}
      }
    },
    "output": {
      "format": "wav",
      "quality": "high",
      "visualization": {"enabled": true}
    }
  }'

# 2. Test the profile
config-cli test-profile podcast_production --audio episode_draft.wav

# 3. Process episode
audio-segmenter episode_final.wav \
  --profile podcast_production \
  --output segments/ \
  --save-config episode_001_config.yaml

# 4. Review segments and metadata
ls segments/
cat segments/segments.json
```

### Example 4: Batch Processing with Custom Rules

```python
from src.config.settings import ConfigManager
from pathlib import Path

# Create custom profile for interview series
config = ConfigManager(profile="podcast")

# Add interview-specific semantic rules
interview_rules = [
    {
        "name": "detect_guest_introduction",
        "label": "guest_intro",
        "priority": 8,
        "confidence_threshold": 0.7,
        "pattern": {
            "min_duration": 30,
            "max_duration": 180,
            "position": "start",
            "energy_range": {"min": 0.1, "max": 0.6}
        }
    },
    {
        "name": "detect_call_to_action",
        "label": "cta",
        "priority": 7,
        "confidence_threshold": 0.6,
        "pattern": {
            "min_duration": 15,
            "max_duration": 60,
            "position": "end",
            "energy_range": {"min": 0.15, "max": 0.8}
        }
    }
]

# Add rules to configuration
config.set("semantic_labeling.rules",
           config.semantic_rules + interview_rules)

# Add categories
config.set("semantic_labeling.categories.guest_intro", {
    "description": "Guest introduction and background",
    "color": "#9C27B0",
    "min_duration": 20
})

config.set("semantic_labeling.categories.cta", {
    "description": "Call to action and outro",
    "color": "#FF5722",
    "min_duration": 10
})

# Save for batch processing
config.save_profile("interview_series")

# Process multiple episodes
episode_files = list(Path("podcasts/").glob("episode_*.wav"))
for episode_file in episode_files:
    print(f"Processing {episode_file.name}...")
    # Would integrate with actual segmentation pipeline here
```

This configuration system provides a robust, flexible foundation for audio segmentation with semantic labeling across diverse content types. The combination of pre-built profiles, JSON Schema validation, and extensive customization options makes it suitable for both simple use cases and complex production workflows.